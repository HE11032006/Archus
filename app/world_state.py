"""
World State: Archus vocabulary on top of the World Model engine.
Entities: module, run, query (one per distinct SQL text), claim (one per module + metric).
Edges: run -executed-> query, run -asserts-> claim, claim -about-> module,
claim -cites-> query (retrieval), claim -verified_by-> query (independent re-query).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .world_model import WorldModel

# Which retrieval category produced each metric the Analyst can claim
METRIC_TO_CATEGORY = {
    "complexity_max": "module_metrics",
    "complexity_avg": "module_metrics",
    "coupling_score": "module_metrics",
    "cohesion_score": "module_metrics",
    "coverage_estimate": "tests",
    "test_file_count": "tests",
    "god_class_count": "antipatterns",
    "hotspot_fixes": "hotspots",
    "outdated_deps": "dependencies",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def source(agent: str, run_id: str) -> Dict[str, Any]:
    return {"kind": agent, "at": now_iso(), "run_id": run_id}


def module_id(repo: str, module_path: Optional[str]) -> str:
    return f"module:{repo}:{module_path or '*'}"


def run_id_of(run_id: str) -> str:
    return f"run:archus:{run_id}"


def query_id(sql: str) -> str:
    return f"query:sql:{hashlib.sha256(sql.encode('utf-8')).hexdigest()[:16]}"


def claim_id(repo: str, module_path: Optional[str], metric: str) -> str:
    return f"claim:{repo}/{module_path or '*'}:{metric}"


def record_run(world: WorldModel, run_id: str, query: str, repo: str, module_path: Optional[str], sample_mode: bool) -> None:
    src = source("Orchestrator", run_id)
    world.upsert_entity("module", external_key={"system": repo, "id": module_path or "*"},
                        attrs={"repo": repo, "module_path": module_path}, source=src)
    run = world.upsert_entity("run", external_key={"system": "archus", "id": run_id},
                              attrs={"query": query, "repo": repo, "module_path": module_path,
                                     "sample_mode": sample_mode, "status": "running"}, source=src)
    world.relate(run["id"], "targets", module_id(repo, module_path), source=src, valid_from=run["first_seen_at"])


def record_query(world: WorldModel, agent: str, run_id: str, repo: str, module_path: Optional[str],
                 sql: str, category: str, rows_count: Optional[int], status: str) -> str:
    src = source(agent, run_id)
    entity = world.upsert_entity("query", external_key={"system": "sql", "id": query_id(sql).split(":")[-1]},
                                 attrs={"sql": sql, "category": category}, source=src)
    world.relate(entity["id"], "about", module_id(repo, module_path), source=src, valid_from=entity["first_seen_at"])
    world.relate(run_id_of(run_id), "executed", entity["id"], source=src, cardinality="many",
                 props={"agent": agent, "rows_count": rows_count, "status": status})
    return entity["id"]


def find_run_query(world: WorldModel, run_id: str, category: str) -> Optional[str]:
    for edge in world.edges_of(run_id_of(run_id), via="executed"):
        query = world.get(edge["to"])
        if query and query["attrs"].get("category") == category:
            return query["id"]
    return None


def record_claim(world: WorldModel, run_id: str, repo: str, module_path: Optional[str],
                 claim: Dict[str, Any], revision: int) -> str:
    """AnalystAgent asserts a claim. Resets the verification fields for this run."""
    src = source("AnalystAgent", run_id)
    entity = world.upsert_entity(
        "claim",
        external_key={"system": f"{repo}/{module_path or '*'}", "id": claim["metric"]},
        attrs={
            "text": claim["claim"],
            "metric": claim["metric"],
            "source_table": claim["source_table"],
            "expected_value": claim["expected_value"],
            "asserted_in_run": run_id,
            "revision": revision,
            "status": "proposed",
            "verified": None,
            "actual_value": None,
        },
        source=src,
    )
    world.relate(entity["id"], "about", module_id(repo, module_path), source=src, valid_from=entity["first_seen_at"])
    world.relate(run_id_of(run_id), "asserts", entity["id"], source=src, cardinality="many",
                 props={"revision": revision})
    cited = find_run_query(world, run_id, METRIC_TO_CATEGORY.get(claim["metric"], ""))
    if cited:
        # Stable valid_from (the query's first sighting) makes re-citing the same query a no-op
        world.relate(entity["id"], "cites", cited, source=src, cardinality="many",
                     valid_from=world.get(cited)["first_seen_at"])
    return entity["id"]


def record_verification(world: WorldModel, run_id: str, claim_entity_id: str, expected_rev: int,
                        verify_query_id: str, actual: Any, supported: bool) -> None:
    """EvidenceEvaluatorAgent records its verdict, refusing to overwrite a claim that changed after it was read."""
    src = source("EvidenceEvaluatorAgent", run_id)
    claim = world.get(claim_entity_id)
    assert claim is not None
    world.upsert_entity(
        "claim",
        external_key={"system": claim_entity_id.split(":")[1], "id": claim["attrs"]["metric"]},
        attrs={
            "status": "verified" if supported else "refuted",
            "verified": supported,
            "actual_value": actual,
            "verified_in_run": run_id,
            "verify_query_id": verify_query_id,
        },
        source=src,
        expected_rev=expected_rev,
    )
    world.relate(claim_entity_id, "verified_by", verify_query_id, source=src,
                 props={"actual": actual, "supported": supported, "run_id": run_id})


def record_outcome(world: WorldModel, run_id: str, status: str, decision: Optional[str]) -> None:
    world.upsert_entity("run", external_key={"system": "archus", "id": run_id},
                        attrs={"status": status, "decision": decision}, source=source("Orchestrator", run_id))


def run_lineage(world: WorldModel, run_id: str) -> Optional[Dict[str, Any]]:
    """Read surface: every claim a run asserted, the queries it cites and the query that verified it."""
    run = world.get(run_id_of(run_id))
    if run is None:
        return None

    claims: Dict[str, Dict[str, Any]] = {}
    for edge in world.edges_of(run["id"], via="asserts"):
        claim = world.get(edge["to"])
        if claim is None or claim["id"] in claims or claim["attrs"].get("asserted_in_run") != run_id:
            continue
        verification = next(iter(world.edges_of(claim["id"], via="verified_by")), None)
        verified_in_this_run = bool(verification and verification["props"].get("run_id") == run_id)
        claims[claim["id"]] = {
            "claim_id": claim["id"],
            "text": claim["attrs"].get("text"),
            "metric": claim["attrs"].get("metric"),
            "expected_value": claim["attrs"].get("expected_value"),
            "actual_value": claim["attrs"].get("actual_value") if verified_in_this_run else None,
            "status": claim["attrs"].get("status") if verified_in_this_run else "unchecked",
            "revision": claim["attrs"].get("revision"),
            "cites": [e["to"] for e in world.edges_of(claim["id"], via="cites")],
            "verified_by": verification["to"] if verified_in_this_run else None,
            "rev": claim["rev"],
        }

    queries = []
    for edge in world.edges_of(run["id"], via="executed"):
        query = world.get(edge["to"])
        if query:
            queries.append({"query_id": query["id"], "sql": query["attrs"].get("sql"),
                            "category": query["attrs"].get("category"), **edge["props"]})

    return {
        "run_id": run_id,
        "run_entity": run["id"],
        "query": run["attrs"].get("query"),
        "module": module_id(run["attrs"].get("repo", ""), run["attrs"].get("module_path")),
        "status": run["attrs"].get("status"),
        "decision": run["attrs"].get("decision"),
        "claims": list(claims.values()),
        "queries": queries,
    }
