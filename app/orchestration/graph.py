"""
Orchestration Graph: Explicit state machine driving agent collaboration,
critique feedback loops, and fallback transitions.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from ..config import settings
from ..schemas import AgentInfo, RunResponse, SharedState, StructuredErrorDetail
from ..tracing import Tracer
from ..world_model import WorldModel
from .. import world_state
from ..adapters.sample_data import SampleDataAdapter
from ..adapters.zetaris import ZetarisAdapter, ZetarisConnectionError
from ..agents.planner import PlannerAgent
from ..agents.retriever import RetrieverAgent
from ..agents.analyst import AnalystAgent
from ..agents.evaluator import EvidenceEvaluatorAgent
from ..agents.reporter import ReporterAgent


class OrchestrationGraph:
    def __init__(self, force_sample_mode: bool = False, world: Optional[WorldModel] = None):
        self.sample_adapter = SampleDataAdapter()
        self.zetaris_adapter = ZetarisAdapter()
        self.force_sample_mode = force_sample_mode
        # Shared state every agent reads and writes; persists across runs
        self.world = world if world is not None else WorldModel(db_path=settings.world_model_db)

    def _get_executor(self, sample_mode: bool) -> Callable[[str], List[Dict[str, Any]]]:
        if sample_mode or not settings.is_zetaris_configured():
            return self.sample_adapter.execute_sql

        zetaris_tripped = False

        def zetaris_runner(sql: str) -> List[Dict[str, Any]]:
            nonlocal zetaris_tripped
            if zetaris_tripped:
                return self.sample_adapter.execute_sql(sql)

            try:
                return self.zetaris_adapter.execute_sql(sql)
            except ZetarisConnectionError as exc:
                # Graceful degradation & Circuit Breaker: Trip fallback for remainder of this run
                zetaris_tripped = True
                print(f"[WARN] Zetaris connection error: {exc}. Circuit breaker tripped -> Degraded fallback to Sample SQLite.")
                return self.sample_adapter.execute_sql(sql)

        return zetaris_runner

    def execute_run(
        self,
        query: str,
        repo: str = "django_app",
        module_path: str | None = None,
        sample_mode: bool | None = None
    ) -> RunResponse:
        start_time = time.perf_counter()

        run_id = str(uuid.uuid4())[:8]
        trace_id = f"trace-{uuid.uuid4()}"
        tracer = Tracer(run_id=run_id, trace_id=trace_id)

        # Determine mode
        is_sample = True if (self.force_sample_mode or sample_mode is True or settings.sample_mode_env) else False
        if not settings.is_zetaris_configured():
            is_sample = True

        state = SharedState(
            run_id=run_id,
            trace_id=trace_id,
            query=query,
            repo=repo,
            module_path=module_path,
            sample_mode=is_sample,
            max_revisions=settings.max_revision_cycles
        )

        tracer.log(
            agent="Orchestrator",
            event="run_initialized",
            payload={
                "run_id": run_id,
                "trace_id": trace_id,
                "sample_mode": is_sample,
                "query": query,
                "repo": repo,
                "module": module_path
            }
        )

        query_executor = self._get_executor(is_sample)
        world_state.record_run(self.world, run_id, query, repo, module_path, is_sample)

        # Instantiate agents
        planner = PlannerAgent(tracer)
        retriever = RetrieverAgent(tracer, query_executor, self.world)
        analyst = AnalystAgent(tracer, self.world)
        evaluator = EvidenceEvaluatorAgent(tracer, query_executor, self.world)
        reporter = ReporterAgent(tracer, self.world)

        agents_registry = [
            AgentInfo(name=planner.name, role=planner.role),
            AgentInfo(name=retriever.name, role=retriever.role),
            AgentInfo(name=analyst.name, role=analyst.role),
            AgentInfo(name=evaluator.name, role=evaluator.role),
            AgentInfo(name=reporter.name, role=reporter.role),
        ]

        try:
            # Step 1: Planning
            state = planner.plan(state)

            # Step 2: Metric Retrieval
            state = retriever.retrieve(state)

            # Step 3 & 4: Collaboration Loop (Analyst <-> Evaluator)
            while True:
                state = analyst.analyze(state)
                state = evaluator.evaluate(state)

                if state.evaluator_status == "needs_revision":
                    tracer.log(
                        agent="Orchestrator",
                        event="revision_loop_back_to_analyst",
                        payload={"revision_count": state.revision_count, "feedback": state.evaluator_feedback}
                    )
                    continue
                else:
                    # Either "approved" or "abstain"
                    break

            # Step 5: Reporting
            state = reporter.report(state)

            elapsed_sec = round(time.perf_counter() - start_time, 3)

            run_status = "success"
            if state.final_output and state.final_output.decision == "insufficient_evidence":
                run_status = "insufficient_evidence"

            world_state.record_outcome(
                self.world, run_id, run_status, state.final_output.decision if state.final_output else None
            )

            tracer.log(
                agent="Orchestrator",
                event="run_completed",
                status=run_status,
                duration_ms=elapsed_sec * 1000,
                payload={"decision": state.final_output.decision if state.final_output else None}
            )

            return RunResponse(
                run_id=run_id,
                status=run_status,
                output=state.final_output,
                agents=agents_registry,
                trace_id=trace_id,
                log_file=str(tracer.log_file_path),
                execution_time_seconds=elapsed_sec
            )

        except Exception as e:
            elapsed_sec = round(time.perf_counter() - start_time, 3)
            try:
                world_state.record_outcome(self.world, run_id, "error", None)
            except Exception:
                pass
            tracer.log(
                agent="Orchestrator",
                event="run_failed",
                status="error",
                duration_ms=elapsed_sec * 1000,
                payload={"error": str(e)}
            )
            return RunResponse(
                run_id=run_id,
                status="error",
                error=StructuredErrorDetail(
                    type=type(e).__name__,
                    message=str(e),
                    recoverable=False
                ),
                agents=agents_registry,
                trace_id=trace_id,
                log_file=str(tracer.log_file_path),
                execution_time_seconds=elapsed_sec
            )
