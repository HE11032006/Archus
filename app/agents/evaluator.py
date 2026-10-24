"""
EvidenceEvaluatorAgent: Veto & verification authority.
Independently verifies every claim against Zetaris / SQLite before approval.
Enforces critique loops (needs_revision) or triggers abstention (insufficient_evidence).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List
from ..schemas import EvidenceItem, SharedState
from ..tracing import Tracer


class EvidenceEvaluatorAgent:
    def __init__(self, tracer: Tracer, query_executor: Callable[[str], List[Dict[str, Any]]]):
        self.name = "EvidenceEvaluatorAgent"
        self.role = "Veto Authority & Independent Evidence Verification"
        self.tracer = tracer
        self.query_executor = query_executor

    def evaluate(self, state: SharedState) -> SharedState:
        self.tracer.log(
            agent=self.name,
            event="evaluation_started",
            payload={"claims_to_check": len(state.claims_to_verify), "revision_count": state.revision_count}
        )

        verified_evidence: List[EvidenceItem] = []
        unsupported_claims: List[str] = []

        repo = state.repo
        module = state.module_path

        # Case 1: If there is zero data or analyst explicitly flagged insufficient evidence
        if state.proposed_decision == "insufficient_evidence" or len(state.claims_to_verify) == 0:
            self.tracer.log(
                agent=self.name,
                event="abstention_triggered",
                status="insufficient_evidence",
                payload={"reason": "Critical baseline metrics missing from catalog.", "missing": state.missing_evidence}
            )
            state.evaluator_status = "abstain"
            state.proposed_decision = "insufficient_evidence"
            return state

        # Case 2: Independently re-query DataAccess to verify each specific claim
        for claim_info in state.claims_to_verify:
            metric = claim_info["metric"]
            source_table = claim_info["source_table"]
            claim_text = claim_info["claim"]
            expected = claim_info["expected_value"]

            # Formulate independent verification query
            if source_table == "modules":
                verify_sql = f"SELECT {metric} FROM modules WHERE repo_id = '{repo}'"
                if module:
                    verify_sql += f" AND module_path = '{module}'"
                verify_sql += " LIMIT 1"
            elif source_table == "tests":
                verify_sql = f"SELECT {metric} FROM tests WHERE repo_id = '{repo}'"
                if module:
                    verify_sql += f" AND module_path = '{module}'"
                verify_sql += " LIMIT 1"
            elif source_table == "antipatterns" and metric == "god_class_count":
                verify_sql = f"SELECT count(*) as count FROM antipatterns WHERE repo_id = '{repo}' AND pattern = 'god_class'"
                if module:
                    verify_sql += f" AND module_path = '{module}'"
                verify_sql += " LIMIT 1"
            else:
                verify_sql = f"SELECT 1 as verified LIMIT 1"

            start_t = time.perf_counter()
            try:
                rows = self.query_executor(verify_sql)
                duration_ms = (time.perf_counter() - start_t) * 1000

                actual_val = None
                if rows:
                    first_row = rows[0]
                    # Get value regardless of column alias key
                    if metric in first_row:
                        actual_val = first_row[metric]
                    elif "count" in first_row:
                        actual_val = first_row["count"]
                    else:
                        actual_val = list(first_row.values())[0]

                # Strict check: expected vs verified
                is_supported = (actual_val is not None) and (str(actual_val) == str(expected))

                self.tracer.log(
                    agent=self.name,
                    event="claim_verified",
                    status="ok" if is_supported else "unsupported",
                    duration_ms=duration_ms,
                    payload={
                        "claim": claim_text,
                        "sql_used": verify_sql,
                        "expected": expected,
                        "actual": actual_val,
                        "supported": is_supported
                    }
                )

                if is_supported:
                    verified_evidence.append(
                        EvidenceItem(
                            claim=claim_text,
                            metric=metric,
                            source_table=source_table,
                            sql_query=verify_sql,
                            value=actual_val,
                            verified=True
                        )
                    )
                else:
                    unsupported_claims.append(f"Claim '{claim_text}' could not be confirmed (actual: {actual_val}).")

            except Exception as e:
                duration_ms = (time.perf_counter() - start_t) * 1000
                self.tracer.log(
                    agent=self.name,
                    event="verification_query_error",
                    status="error",
                    duration_ms=duration_ms,
                    payload={"sql": verify_sql, "error": str(e)}
                )
                unsupported_claims.append(f"SQL verification error on claim '{claim_text}': {e}")

        state.verified_evidence = verified_evidence

        # Check approval or feedback loop
        if unsupported_claims:
            if state.revision_count < state.max_revisions:
                state.revision_count += 1
                state.evaluator_status = "needs_revision"
                state.evaluator_feedback = f"Revision #{state.revision_count}: " + " | ".join(unsupported_claims)

                self.tracer.log(
                    agent=self.name,
                    event="critique_loop_triggered",
                    status="needs_revision",
                    payload={"feedback": state.evaluator_feedback, "revision_count": state.revision_count}
                )
            else:
                # Max revisions reached with unproven claims -> abstain
                state.evaluator_status = "abstain"
                state.proposed_decision = "insufficient_evidence"
                state.missing_evidence.extend(unsupported_claims)

                self.tracer.log(
                    agent=self.name,
                    event="abstention_triggered",
                    status="insufficient_evidence",
                    payload={"reason": "Max revision cycles reached without solid evidentiary backing."}
                )
        else:
            state.evaluator_status = "approved"
            self.tracer.log(
                agent=self.name,
                event="evidence_approved",
                status="ok",
                payload={"verified_evidence_count": len(verified_evidence)}
            )

        return state
