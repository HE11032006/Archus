"""
RetrieverAgent: Executes planned SQL queries against the active data access layer
(Zetaris in LIVE mode or local SQLite in SAMPLE mode).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List
from ..schemas import SharedState
from ..tracing import Tracer


class RetrieverAgent:
    def __init__(self, tracer: Tracer, query_executor: Callable[[str], List[Dict[str, Any]]]):
        self.name = "RetrieverAgent"
        self.role = "Data Access & Query Execution"
        self.tracer = tracer
        self.query_executor = query_executor

    def retrieve(self, state: SharedState) -> SharedState:
        self.tracer.log(
            agent=self.name,
            event="retrieval_started",
            payload={"queries_to_run": len(state.planned_queries), "sample_mode": state.sample_mode}
        )

        retrieved: Dict[str, Any] = {}

        for item in state.planned_queries:
            category = item["category"]
            sql = item["sql"]
            start_t = time.perf_counter()

            try:
                rows = self.query_executor(sql)
                duration_ms = (time.perf_counter() - start_t) * 1000
                retrieved[category] = rows

                state.sql_history.append({
                    "sql": sql,
                    "category": category,
                    "rows_count": len(rows),
                    "duration_ms": duration_ms,
                    "status": "success"
                })

                self.tracer.log(
                    agent=self.name,
                    event="sql_executed",
                    status="ok",
                    duration_ms=duration_ms,
                    payload={"category": category, "sql": sql, "rows_count": len(rows)}
                )

            except Exception as e:
                duration_ms = (time.perf_counter() - start_t) * 1000
                state.sql_history.append({
                    "sql": sql,
                    "category": category,
                    "status": "error",
                    "error": str(e),
                    "duration_ms": duration_ms
                })

                self.tracer.log(
                    agent=self.name,
                    event="sql_failed",
                    status="error",
                    duration_ms=duration_ms,
                    payload={"category": category, "sql": sql, "error": str(e)}
                )

        state.retrieved_data = retrieved
        self.tracer.log(
            agent=self.name,
            event="retrieval_completed",
            payload={"categories_collected": list(retrieved.keys())}
        )
        return state
