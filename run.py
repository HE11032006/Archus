"""
run.py: Main entrypoint for Archus application.
Provides FastAPI HTTP endpoints (POST /run, GET /health) and optional CLI direct execution.
"""

from __future__ import annotations

import argparse
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.orchestration.graph import OrchestrationGraph
from app.schemas import RunRequest, RunResponse
from app.world_state import run_lineage
from app.llm import llm_client

app = FastAPI(
    title="Archus Multi-Agent Architecture Decision Service",
    description="Explains whether to maintain, refactor, or migrate software modules based on verified Zetaris metrics.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = OrchestrationGraph()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Archus",
        "version": "0.1.0",
        "sample_mode_enabled": settings.sample_mode_env or not settings.is_zetaris_configured(),
        "zetaris_configured": settings.is_zetaris_configured(),
        "meterless_configured": settings.is_model_configured(),
        "llm_provider": llm_client.provider_id,
    }


@app.get("/providers")
def list_providers():
    """Model providers and which one Archus uses. Read-only: connect with scripts/meterless.py."""
    runtime = llm_client.providers["meterless"]
    return {
        "active": llm_client.provider_id,
        "providers": [
            {"id": runtime.id, "name": runtime.name, **runtime.status()},
            {"id": "openai_compatible", "name": "OpenAI-compatible (MODEL_BASE_URL)",
             "base_url": settings.model_base_url, "model": settings.model_name,
             "configured": settings.is_model_configured()},
        ],
    }


@app.get("/providers/meterless/status")
def meterless_status():
    """online, unauthorized (paste the token with scripts/meterless.py token) or offline."""
    return llm_client.providers["meterless"].status()


@app.post("/run", response_model=RunResponse)
def run_endpoint(request: RunRequest):
    """
    Main programmatic entrypoint for judges and Tech Leads.
    Takes a query + repo context, coordinates agents, and returns a verified decision record.
    """
    sample_mode = request.options.sample_mode if request.options else None
    provider = request.options.provider if request.options else None
    model = request.options.model if request.options else None

    response = graph.execute_run(
        query=request.input.query,
        repo=request.input.repo,
        module_path=request.input.module_path,
        sample_mode=sample_mode,
        provider=provider,
        model=model
    )

    if response.status == "error":
        # Still return 200 with structured error object per hackathon spec, or 500 if critical
        pass

    return response


@app.get("/world/stats")
def world_stats():
    """World Model health: schema version, record counts, orphans, audit length."""
    return graph.world.stats()


@app.get("/world/runs/{run_id}")
def world_run_lineage(run_id: str):
    """Every claim a run asserted, the queries it was drawn from and the query that verified it."""
    lineage = run_lineage(graph.world, run_id)
    if lineage is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found in the World Model")
    return lineage


@app.get("/world/entities/{entity_id:path}")
def world_entity(entity_id: str):
    """One World Model entity with its open outgoing and incoming edges."""
    entity = graph.world.get(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found in the World Model")
    return {
        "entity": entity,
        "edges_out": graph.world.edges_of(entity_id, direction="out"),
        "edges_in": graph.world.edges_of(entity_id, direction="in"),
    }


def cli_main():
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Archus Decision Engine CLI")
    parser.add_argument("--input", "-i", type=str, default=None, help="Path to input JSON file (e.g. input_examples/example_1_refactor.json)")
    parser.add_argument("--query", "-q", type=str, default="Should we refactor or maintain the accounts module?", help="Question for the agent")
    parser.add_argument("--repo", "-r", type=str, default="django_app", help="Repository identifier")
    parser.add_argument("--module", "-m", type=str, default="accounts", help="Module path to analyze")
    parser.add_argument("--sample", action="store_true", help="Force sample mode (SQLite local)")
    parser.add_argument("--json", action="store_true", help="Print raw JSON response to stdout")
    parser.add_argument("--provider", choices=["meterless", "openai_compatible", "none"], default=None,
                        help="Model provider for this run (default: LLM_PROVIDER, else meterless)")
    parser.add_argument("--model", default=None,
                        help="Meterless routing mode for this run, e.g. meterless/deep (default: saved mode, else meterless/auto)")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI server instead of single run")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to bind server")
    args = parser.parse_args()
    if args.model:
        from app.adapters.meterless_runtime import MeterlessModeError, validate_mode
        try:
            validate_mode(args.model)
        except MeterlessModeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)

    if args.serve or (len(sys.argv) == 1 and not args.input):
        print(f"Starting Archus Server on {settings.host}:{args.port}...")
        uvicorn.run(app, host=settings.host, port=args.port)
    else:
        query = args.query
        repo = args.repo
        module_path = args.module
        sample_mode = args.sample

        if args.input:
            input_file = Path(args.input)
            if not input_file.exists():
                print(f"Error: Input file {args.input} does not exist.", file=sys.stderr)
                sys.exit(1)
            with open(input_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            inp = payload.get("input", {})
            query = inp.get("query", query)
            repo = inp.get("repo", repo)
            module_path = inp.get("module_path", module_path)
            opts = payload.get("options", {})
            if "sample_mode" in opts and not args.sample:
                sample_mode = opts["sample_mode"]

        if not args.json:
            print(f"\n[CLI] Running single query evaluation...")
        result = graph.execute_run(
            query=query,
            repo=repo,
            module_path=module_path,
            sample_mode=sample_mode,
            provider=args.provider,
            model=args.model
        )

        if args.json:
            print(json.dumps(result.model_dump(), indent=2, default=str))
            return
        print("\n" + "=" * 60)
        print(f"RUN ID: {result.run_id} | STATUS: {result.status.upper()}")
        if result.output:
            print(f"DECISION: {result.output.decision.upper()} (Confidence: {result.output.confidence * 100:.0f}%)")
            print(f"SUMMARY: {result.output.summary}")
            mp = result.output.model_provider or {}
            if mp.get("provider") == "rules":
                print(f"WRITTEN BY: rules (selected provider '{mp.get('selected')}' did not answer)")
            else:
                print(f"WRITTEN BY: {mp.get('provider')} | {mp.get('model_requested')} -> {mp.get('model_served')}"
                      + (" (fallback)" if mp.get("fallback") else ""))
            print(f"VERIFIED EVIDENCE ITEMS: {len(result.output.evidence)}")
            for idx, ev in enumerate(result.output.evidence, 1):
                print(f"  [{idx}] {ev.claim} (Table: {ev.source_table}, Verified: {ev.verified})")
                if ev.claim_id:
                    print(f"      World Model: {ev.claim_id} <- verified by {ev.verified_by_query_id}")
            if result.output.action_plan:
                print("ACTION PLAN:")
                for step in result.output.action_plan:
                    print(f"  - {step}")
            if result.output.missing_data:
                print("MISSING DATA / LIMITATIONS:")
                for m in result.output.missing_data:
                    print(f"  ! {m}")
        elif result.error:
            print(f"ERROR: {result.error.message}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    cli_main()
