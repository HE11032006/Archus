"""
AnalystAgent: Evaluates options (maintain/refactor/migrate) using metric scoring
and drafts factual claims for the EvidenceEvaluator to verify.
"""

from __future__ import annotations

from typing import Any, Dict, List
from ..schemas import SharedState
from ..scoring import evaluate_options
from ..tracing import Tracer
from ..world_model import WorldModel
from .. import world_state


class AnalystAgent:
    def __init__(self, tracer: Tracer, world: WorldModel):
        self.name = "AnalystAgent"
        self.role = "Architectural Trade-off Analysis & Metric Evaluation"
        self.tracer = tracer
        self.world = world

    def analyze(self, state: SharedState) -> SharedState:
        self.tracer.log(
            agent=self.name,
            event="analysis_started",
            payload={"revision": state.revision_count, "prior_feedback": state.evaluator_feedback}
        )

        data = state.retrieved_data
        modules_rows = data.get("module_metrics", [])
        antipatterns_rows = data.get("antipatterns", [])
        tests_rows = data.get("tests", [])
        hotspots_rows = data.get("hotspots", [])
        deps_rows = data.get("dependencies", [])

        # Build composite metrics summary
        primary_module = modules_rows[0] if modules_rows else {}
        test_info = tests_rows[0] if tests_rows else {}

        god_classes = sum(1 for a in antipatterns_rows if a.get("pattern") == "god_class")
        total_fixes = sum(int(h.get("fix_count", 0)) for h in hotspots_rows)
        outdated_deps = sum(1 for d in deps_rows if d.get("is_outdated"))

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
            "outdated_deps": outdated_deps,
        }

        # Run scoring engine
        decision, confidence, comparisons, missing = evaluate_options(metrics_summary)
        state.proposed_decision = decision
        state.missing_evidence = missing

        # Prepare specific claims to be independently proven by EvidenceEvaluator
        claims: List[Dict[str, Any]] = []

        if metrics_summary["complexity_max"] is not None:
            claims.append({
                "claim": f"Maximum cyclomatic complexity is {metrics_summary['complexity_max']}",
                "metric": "complexity_max",
                "source_table": "modules",
                "expected_value": metrics_summary["complexity_max"]
            })

        if metrics_summary["coverage_estimate"] is not None:
            claims.append({
                "claim": f"Test coverage estimate is {metrics_summary['coverage_estimate']}%",
                "metric": "coverage_estimate",
                "source_table": "tests",
                "expected_value": metrics_summary["coverage_estimate"]
            })

        if metrics_summary["coupling_score"] is not None:
            claims.append({
                "claim": f"Module coupling score is {metrics_summary['coupling_score']}",
                "metric": "coupling_score",
                "source_table": "modules",
                "expected_value": metrics_summary["coupling_score"]
            })

        claims.append({
            "claim": f"Detected {god_classes} God Class antipattern(s)",
            "metric": "god_class_count",
            "source_table": "antipatterns",
            "expected_value": god_classes
        })

        # Publish each claim to the World Model; the Evaluator reads it back from there
        for claim in claims:
            claim["claim_id"] = world_state.record_claim(
                self.world, state.run_id, state.repo, state.module_path, claim, state.revision_count
            )

        state.claims_to_verify = claims
        self.tracer.log(
            agent=self.name,
            event="analysis_completed",
            payload={
                "proposed_decision": decision,
                "confidence": confidence,
                "claims_generated": len(claims),
                "missing_data_count": len(missing)
            }
        )
        return state
