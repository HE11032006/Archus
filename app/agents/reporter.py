"""
ReporterAgent: Synthesizes approved evidence and structured decisions
into a formal architecture decision record with an actionable plan.
"""

from __future__ import annotations

from typing import List
from ..schemas import OptionComparison, RunOutput, SharedState
from ..scoring import evaluate_options
from ..llm import llm_client
from ..tracing import Tracer
from ..world_model import WorldModel
from .. import world_state


class ReporterAgent:
    def __init__(self, tracer: Tracer, world: WorldModel):
        self.name = "ReporterAgent"
        self.role = "Formal Decision Record Synthesis & Action Plan Generation"
        self.tracer = tracer
        self.world = world

    def report(self, state: SharedState) -> SharedState:
        self.tracer.log(
            agent=self.name,
            event="reporting_started",
            payload={"decision": state.proposed_decision, "evaluator_status": state.evaluator_status}
        )

        decision = state.proposed_decision or "insufficient_evidence"
        action_plan: List[str] = []

        if decision == "insufficient_evidence":
            summary = (
                f"Abstention on repository '{state.repo}' (module: '{state.module_path or 'all'}'). "
                "The agent refuses to conclude because mandatory baseline metrics (such as unit test coverage, "
                "cyclomatic complexity, or dependency catalogs) are unverified or absent from the data store. "
                "Recommended action: run complete static and dynamic analysis before committing to an architectural decision."
            )
            confidence = 0.2
            action_plan = [
                "Instrument the codebase with automated test coverage runners (pytest-cov).",
                "Execute the ArchX collector on the local source to generate missing module metrics.",
                "Populate the metrics database and re-evaluate with verified data."
            ]
        elif decision == "maintain":
            summary = (
                f"Decision: MAINTAIN for module '{state.module_path or state.repo}'. "
                "The module exhibits low cyclomatic complexity, solid architectural cohesion, and acceptable maintenance churn. "
                "Existing structural integrity remains within safe operating bounds."
            )
            confidence = 0.85
            action_plan = [
                "Keep existing code active with routine dependency security patching.",
                "Maintain test suite health and monitor change hotspots for complexity spikes.",
                "Review again in 6 months or if cyclomatic complexity exceeds threshold 20."
            ]
        elif decision == "refactor":
            summary = (
                f"Decision: REFACTOR for module '{state.module_path or state.repo}'. "
                "While the module has active test suites that safeguard behavioral regressions, specific structural smells "
                "(long methods or localized high coupling) are creating friction. Internal restructuring without external API change is recommended."
            )
            confidence = 0.80
            action_plan = [
                "Decompose long methods into pure helper functions covered by existing tests.",
                "Decouple cross-module references using dependency inversion.",
                "Increase test coverage on uncovered edge-case branches before refactoring."
            ]
        elif decision == "migrate":
            summary = (
                f"Decision: MIGRATE for module '{state.module_path or state.repo}'. "
                "The module presents severe architectural debt, multiple God Classes, critical coupling, and insufficient test harnesses. "
                "Incremental refactoring carries high regression risk; a strangler-fig migration to a modern service or rewrite is recommended."
            )
            confidence = 0.82
            action_plan = [
                "Define boundary interfaces around the legacy module to prevent further coupling.",
                "Construct end-to-end black-box characterization tests to capture current behavior.",
                "Incrementally migrate capabilities using the Strangler Fig pattern."
            ]
        else:
            summary = f"Decision: {decision.upper()} based on verified architectural metrics."
            confidence = 0.5

        # Re-derive comparisons for completeness
        data = state.retrieved_data
        modules_rows = data.get("module_metrics", [])
        tests_rows = data.get("tests", [])
        antipatterns_rows = data.get("antipatterns", [])
        hotspots_rows = data.get("hotspots", [])

        primary_module = modules_rows[0] if modules_rows else {}
        test_info = tests_rows[0] if tests_rows else {}
        god_classes = sum(1 for a in antipatterns_rows if a.get("pattern") == "god_class")
        total_fixes = sum(int(h.get("fix_count", 0)) for h in hotspots_rows)

        metrics_summary = {
            "loc": primary_module.get("loc"),
            "complexity_avg": primary_module.get("complexity_avg"),
            "complexity_max": primary_module.get("complexity_max"),
            "coupling_score": primary_module.get("coupling_score"),
            "cohesion_score": primary_module.get("cohesion_score"),
            "god_class_count": god_classes,
            "test_file_count": test_info.get("test_file_count"),
            "coverage_estimate": test_info.get("coverage_estimate"),
            "hotspot_fixes": total_fixes,
        }
        _, _, comparisons, _ = evaluate_options(metrics_summary)

        # Optional LLM polish if model is reachable
        if not state.sample_mode and llm_client.meterless.is_available():
            llm_prompt = (
                f"Question: {state.query}\n"
                f"Decision: {decision}\n"
                f"Verified evidence: {[e.model_dump() for e in state.verified_evidence]}\n"
                "Write a 2-sentence executive summary for the Tech Lead explaining WHY this decision is justified."
            )
            polished = llm_client.generate(llm_prompt)
            if polished and len(polished.strip()) > 20:
                summary = polished.strip()

        # Link every evidence item to its claim, cited queries and verifying query in the World Model
        lineage = world_state.run_lineage(self.world, state.run_id) or {"claims": []}
        lineage_by_metric = {c["metric"]: c for c in lineage["claims"]}
        for item in state.verified_evidence:
            entry = lineage_by_metric.get(item.metric)
            if entry:
                item.claim_id = entry["claim_id"]
                item.cited_query_ids = entry["cites"]
                item.verified_by_query_id = entry["verified_by"]

        output = RunOutput(
            decision=decision,
            confidence=confidence,
            options_compared=comparisons,
            evidence=state.verified_evidence,
            missing_data=state.missing_evidence,
            action_plan=action_plan,
            summary=summary,
            world_model={
                "run_entity": world_state.run_id_of(state.run_id),
                "claims": len(lineage["claims"]),
                "lineage_endpoint": f"/world/runs/{state.run_id}",
            },
        )

        state.final_output = output
        self.tracer.log(
            agent=self.name,
            event="reporting_completed",
            payload={"decision": decision, "verified_evidence_items": len(state.verified_evidence)}
        )
        return state
