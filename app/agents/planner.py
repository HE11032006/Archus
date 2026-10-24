"""
PlannerAgent: Breaks down the tech lead query into testable criteria
and plans the necessary SQL queries to execute against the code metrics catalog.
"""

from __future__ import annotations

from typing import Any, Dict, List
from ..schemas import SharedState
from ..tracing import Tracer


class PlannerAgent:
    def __init__(self, tracer: Tracer):
        self.name = "PlannerAgent"
        self.role = "Query Decomposition and Metric Retrieval Planning"
        self.tracer = tracer

    def plan(self, state: SharedState) -> SharedState:
        self.tracer.log(
            agent=self.name,
            event="planning_started",
            payload={"query": state.query, "repo": state.repo, "module": state.module_path}
        )

        criteria = [
            "code_volume_and_complexity",
            "antipatterns_and_god_classes",
            "test_coverage_and_test_harness",
            "coupling_and_cohesion",
            "git_churn_and_fix_hotspots",
            "outdated_dependencies"
        ]
        state.plan_criteria = criteria

        # Build parameterized read-only queries for the target repo & module
        repo = state.repo
        module = state.module_path

        queries: List[Dict[str, str]] = []

        # 1. Module metrics
        if module:
            queries.append({
                "category": "module_metrics",
                "sql": f"SELECT repo_id, module_path, loc, function_count, class_count, complexity_avg, complexity_max, coupling_score, cohesion_score FROM modules WHERE repo_id = '{repo}' AND module_path = '{module}' LIMIT 10"
            })
        else:
            queries.append({
                "category": "module_metrics",
                "sql": f"SELECT repo_id, module_path, loc, function_count, class_count, complexity_avg, complexity_max, coupling_score, cohesion_score FROM modules WHERE repo_id = '{repo}' ORDER BY complexity_max DESC LIMIT 10"
            })

        # 2. Antipatterns
        if module:
            queries.append({
                "category": "antipatterns",
                "sql": f"SELECT pattern, file, severity, value FROM antipatterns WHERE repo_id = '{repo}' AND module_path = '{module}' LIMIT 50"
            })
        else:
            queries.append({
                "category": "antipatterns",
                "sql": f"SELECT pattern, file, severity, value FROM antipatterns WHERE repo_id = '{repo}' LIMIT 50"
            })

        # 3. Tests
        if module:
            queries.append({
                "category": "tests",
                "sql": f"SELECT test_file_count, test_loc, coverage_estimate FROM tests WHERE repo_id = '{repo}' AND module_path = '{module}' LIMIT 10"
            })
        else:
            queries.append({
                "category": "tests",
                "sql": f"SELECT module_path, test_file_count, test_loc, coverage_estimate FROM tests WHERE repo_id = '{repo}' LIMIT 20"
            })

        # 4. Hotspots (Anonymized changes and fixes)
        if module:
            queries.append({
                "category": "hotspots",
                "sql": f"SELECT file, change_count, fix_count FROM hotspots WHERE repo_id = '{repo}' AND module_path = '{module}' ORDER BY fix_count DESC LIMIT 10"
            })
        else:
            queries.append({
                "category": "hotspots",
                "sql": f"SELECT file, change_count, fix_count FROM hotspots WHERE repo_id = '{repo}' ORDER BY fix_count DESC LIMIT 10"
            })

        # 5. Outdated Dependencies
        queries.append({
            "category": "dependencies",
            "sql": f"SELECT name, version, latest_version, is_outdated FROM dependencies WHERE repo_id = '{repo}' AND is_outdated = 1 LIMIT 20"
        })

        state.planned_queries = queries
        self.tracer.log(
            agent=self.name,
            event="planning_completed",
            payload={"criteria_count": len(criteria), "planned_queries_count": len(queries)}
        )
        return state
