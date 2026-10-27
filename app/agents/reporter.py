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

        # LLM Synthesis through Meterless Runtime (or other provider)
        provider_record = {"selected": state.llm_provider or llm_client.provider_id, "provider": "rules"}
        analysis = state.repo_analysis or {}
        arch_style = analysis.get("architecture_pattern", "Layered / Modular Architecture")
        repo_name = analysis.get("repo_name", state.repo)
        lang = analysis.get("primary_language", "Software")
        hotspots = analysis.get("complexity_hotspots", [])
        anti_list = analysis.get("anti_patterns", [])

        # Default rich multi-paragraph explanation (used as fallback or baseline)
        detailed_explanation = _build_default_detailed_report(
            decision=decision,
            repo_name=repo_name,
            arch_style=arch_style,
            lang=lang,
            metrics=metrics_summary,
            anti_patterns=anti_list,
            hotspots=hotspots,
            comparisons=comparisons,
        )

        if llm_client.is_available(state.llm_provider):
            evidence_summary = [f"{e.metric}: {e.value} (verified: {e.verified})" for e in state.verified_evidence]
            llm_prompt = (
                f"You are Archus, a Senior Enterprise Software Architect.\n"
                f"Repository: {repo_name} ({lang})\n"
                f"Detected Architecture Style: {arch_style}\n"
                f"User Question: {state.query}\n"
                f"Definitive Decision: {decision.upper()} (Confidence: {int(confidence * 100)}%)\n"
                f"Verified AST & Database Metrics:\n"
                f"- Max Cyclomatic Complexity: {metrics_summary.get('complexity_max')}\n"
                f"- Avg Cyclomatic Complexity: {metrics_summary.get('complexity_avg')}\n"
                f"- Coupling Score: {metrics_summary.get('coupling_score')}\n"
                f"- Cohesion Score: {metrics_summary.get('cohesion_score')}\n"
                f"- Test Coverage Estimate: {metrics_summary.get('coverage_estimate')}%\n"
                f"- Anti-Patterns Found: {len(anti_list)} (God Classes: {god_classes})\n"
                f"- Complexity Hotspot Files: {[h.get('file') for h in hotspots[:3]]}\n"
                f"Verified SQL Evidence: {evidence_summary}\n\n"
                "Please provide a comprehensive, authoritative Software Architecture Report with the following structured sections:\n"
                "### 1. Executive Verdict & Core Architecture Diagnostics\n"
                "Explain the primary technical rationale for this decision.\n\n"
                "### 2. Structural Health & Anti-Pattern Analysis\n"
                "Analyze the coupling, cohesion, and specific anti-patterns identified.\n\n"
                "### 3. Strategic Trade-Off Analysis (Maintain vs Refactor vs Migrate)\n"
                "Explain why this path delivers the best ROI and lowest operational blast radius.\n\n"
                "### 4. Phased Strategic Execution Roadmap\n"
                "Outline Phase 1 (Immediate Stabilization), Phase 2 (Core Refactoring / Decoupling), and Phase 3 (Architecture Fitness Functions & CI Guardrails).\n\n"
                "### 5. Risk Assessment & Operational Blast Radius\n"
                "Detail deployment risks, testing precautions, and how to avoid regressions."
            )

            polished_text, provider_record = llm_client.generate_with_meta(
                llm_prompt,
                system_prompt="You are Archus, an elite software architect producing deep, verifiable architecture decision records for engineering leadership.",
                provider_id=state.llm_provider,
                model=state.llm_model,
            )

            if polished_text and len(polished_text.strip()) > 100:
                detailed_explanation = polished_text.strip()
                # Derive a crisp 2-sentence summary from the text or generate one
                summary = (
                    f"Decision: {decision.upper()} for '{repo_name}'. "
                    f"Architecture style: {arch_style}. "
                    f"Based on verified metrics (complexity {metrics_summary.get('complexity_max')}, "
                    f"coupling {metrics_summary.get('coupling_score')}, coverage {metrics_summary.get('coverage_estimate')}%), "
                    f"this strategy minimizes regression risk and stabilizes core technical debt."
                )
            else:
                provider_record["provider"] = "rules"

        self.tracer.log(agent=self.name, event="llm_call", payload=provider_record)

        # Build concrete actionable refactoring recipes
        recipes = _generate_refactoring_recipes(decision, arch_style, anti_list, hotspots)

        # Link every evidence item to its claim, cited queries and verifying query in the World Model
        lineage = world_state.run_lineage(self.world, state.run_id) or {"claims": []}
        lineage_by_metric = {c["metric"]: c for c in lineage["claims"]}
        for item in state.verified_evidence:
            entry = lineage_by_metric.get(item.metric)
            if entry:
                item.claim_id = entry["claim_id"]
                item.cited_query_ids = entry["cites"]
                item.verified_by_query_id = entry["verified_by"]

        repo_meta = {
            "repo_name": repo_name,
            "language": lang,
            "architecture_pattern": arch_style,
            "files_analyzed": analysis.get("files_analyzed", len(modules_rows) or 1),
            "total_loc": analysis.get("total_loc", primary_module.get("loc", 0)),
            "total_functions": analysis.get("total_functions", primary_module.get("function_count", 0)),
            "total_classes": analysis.get("total_classes", primary_module.get("class_count", 0)),
        }

        output = RunOutput(
            decision=decision,
            confidence=confidence,
            options_compared=comparisons,
            evidence=state.verified_evidence,
            missing_data=state.missing_evidence,
            action_plan=action_plan,
            summary=summary,
            detailed_explanation=detailed_explanation,
            architecture_style=arch_style,
            repo_metadata=repo_meta,
            metrics_overview=metrics_summary,
            antipatterns=anti_list[:15],
            complexity_hotspots=hotspots[:10],
            refactoring_recipes=recipes,
            model_provider=provider_record,
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


def _build_default_detailed_report(
    decision: str,
    repo_name: str,
    arch_style: str,
    lang: str,
    metrics: dict,
    anti_patterns: list,
    hotspots: list,
    comparisons: list,
) -> str:
    """Generates a structured, rich architecture report when LLM is in rules mode."""
    lines = [
        f"## Comprehensive Architecture Assessment: {repo_name}",
        f"**Target System**: `{repo_name}` | **Primary Tech**: `{lang}` | **Detected Style**: `{arch_style}`",
        "",
        "### 1. Executive Verdict & Core Architecture Diagnostics",
        f"After verifying static AST metrics through SQLGuard, the system concludes with high confidence on **{decision.upper()}**.",
        f"The codebase demonstrates a maximum cyclomatic complexity of **{metrics.get('complexity_max')}** (average: **{metrics.get('complexity_avg')}**), "
        f"with an architectural coupling index of **{metrics.get('coupling_score')}** and cohesion of **{metrics.get('cohesion_score')}**.",
        f"Estimated automated test coverage stands at **{metrics.get('coverage_estimate')}%**, establishing the safety boundary for any modifications.",
        "",
        "### 2. Structural Health & Anti-Pattern Analysis",
        f"Static inspection detected **{len(anti_patterns)} architectural smells**.",
    ]

    if anti_patterns:
        lines.append("Key anti-patterns identified in the repository:")
        for a in anti_patterns[:5]:
            p = a.get("pattern", "").replace("_", " ").title()
            f = a.get("file", "unknown")
            lines.append(f"- **{p}** in `{f}`: severity `{a.get('severity')}` (metric value: {a.get('value')}).")
    else:
        lines.append("No critical god-classes or toxic cyclomatic hotspots were detected in the primary AST tree.")

    lines.extend([
        "",
        "### 3. Strategic Trade-Off Analysis (Maintain vs Refactor vs Migrate)",
        "Evaluating the trade-off matrix based on verified evidence:",
    ])

    for c in comparisons:
        opt_name = c.option.upper()
        lines.append(f"- **{opt_name} (Suitability Score: {int(c.score)}/100)**: {c.rationale}")

    lines.extend([
        "",
        "### 4. Phased Strategic Execution Roadmap",
        "To ensure business continuity while addressing debt, the recommended 3-phase execution is:",
        "1. **Phase 1: Stabilization & Boundary Enforcement (Weeks 1-2)**: Add black-box characterization tests around high-churn hotspot modules before altering code paths.",
        "2. **Phase 2: Targeted Structural Decoupling (Weeks 3-5)**: Decompose identified God Classes and high-complexity functions into specialized domain handlers using dependency injection.",
        "3. **Phase 3: Architectural Fitness Functions & CI Guardrails (Week 6+)**: Institute automated complexity caps and import linters to prevent architectural decay over future releases.",
        "",
        "### 5. Risk Assessment & Operational Blast Radius",
        "- **Regression Risk**: Moderate. Mitigated by existing test harness and characterization suites.",
        "- **Deployment Blast Radius**: Isolated to internal modules; external public interfaces should preserve backwards compatibility.",
        "- **Estimated Engineering Effort**: 2 to 4 sprints depending on dedicated refactoring allocation."
    ])

    return "\n".join(lines)


def _generate_refactoring_recipes(
    decision: str,
    arch_style: str,
    anti_patterns: list,
    hotspots: list,
) -> list:
    """Generates concrete code refactoring blueprints and transformation recipes."""
    recipes = []

    if decision in ("refactor", "migrate"):
        recipes.append({
            "title": "Extract Domain Service from God Class",
            "pattern": "Extract Service / Single Responsibility",
            "impact": "Reduces coupling by 40% and allows isolated unit testing without database dependencies.",
            "before_snippet": (
                "# BEFORE: Monolithic class handling business logic, persistence, and external calls\n"
                "class AccountManager:\n"
                "    def process_renewal(self, account_id, payment_data):\n"
                "        # 120 lines mixing SQL queries, Stripe API, sending emails, and audit logs\n"
                "        ..."
            ),
            "after_snippet": (
                "# AFTER: Cohesive domain service with injected dependencies\n"
                "class AccountRenewalService:\n"
                "    def __init__(self, payment_gateway: PaymentGateway, notifier: NotificationPort):\n"
                "        self.gateway = payment_gateway\n"
                "        self.notifier = notifier\n\n"
                "    def execute(self, account: Account) -> RenewalResult:\n"
                "        # Pure business logic with verified invariants\n"
                "        ..."
            )
        })

        recipes.append({
            "title": "Decouple Cross-Module Dependencies via Ports & Adapters",
            "pattern": "Dependency Inversion / Ports & Adapters",
            "impact": "Eliminates circular imports and reduces cyclomatic complexity in orchestration layer.",
            "before_snippet": (
                "# BEFORE: Direct tight coupling to third-party SDK and external DB tables\n"
                "from legacy_billing.models import RawInvoice\n"
                "from stripe.api import Charge\n"
                "def bill_user(u): Charge.create(...); RawInvoice.save(...)"
            ),
            "after_snippet": (
                "# AFTER: Pure domain interface decoupling infrastructure from core logic\n"
                "class BillingPort(Protocol):\n"
                "    def charge(self, amount: Money, customer: CustomerId) -> Receipt:\n"
                "        ..."
            )
        })

    if decision == "migrate":
        recipes.append({
            "title": "Strangler Fig Routing Facade",
            "pattern": "Strangler Fig Pattern",
            "impact": "Enables safe incremental microservice or modern module migration with zero downtime.",
            "before_snippet": (
                "# Direct calls to legacy monolithic endpoints\n"
                "curl -X POST https://api.legacy/v1/orders"
            ),
            "after_snippet": (
                "# API Gateway / Proxy routing canary traffic (10% -> 50% -> 100%) to new service\n"
                "location /orders {\n"
                "    proxy_pass http://modern-order-service:8080;\n"
                "}"
            )
        })

    return recipes
