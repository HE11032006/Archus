"""
Deterministic Scoring Engine: Evaluates Maintain, Refactor, and Migrate options
based on quantitative software metrics and standard architectural thresholds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from .schemas import OptionComparison


def evaluate_options(metrics: Dict[str, Any]) -> Tuple[str, float, List[OptionComparison], List[str]]:
    """
    Evaluates module metrics and returns:
    (recommended_decision, confidence, [OptionComparison], missing_data)
    """
    missing_data = []

    # Check for crucial metrics presence
    loc = metrics.get("loc")
    complexity_max = metrics.get("complexity_max")
    coverage = metrics.get("coverage_estimate")
    coupling = metrics.get("coupling_score")
    god_classes = metrics.get("god_class_count", 0)
    fixes = metrics.get("hotspot_fixes", 0)

    if loc is None or complexity_max is None:
        missing_data.append("Module code complexity and size metrics are missing from catalog.")
    if coverage is None:
        missing_data.append("Test coverage data is absent.")

    # If critical data is missing, recommend abstention immediately
    if len(missing_data) >= 2 or loc == 0:
        comparisons = [
            OptionComparison(
                option="maintain",
                score=10.0,
                pros=["Zero immediate engineering cost"],
                cons=["Unknown hidden risks due to unmeasured codebase"],
                rationale="Cannot recommend without foundational metrics."
            ),
            OptionComparison(
                option="refactor",
                score=10.0,
                pros=["Targeted improvements possible"],
                cons=["No regression safety harness (tests unknown)"],
                rationale="Refactoring without metrics or test coverage carries unacceptable risk."
            ),
            OptionComparison(
                option="migrate",
                score=10.0,
                pros=["Clean slate"],
                cons=["High investment with unquantified ROI"],
                rationale="Migration cannot be justified without documented structural failure."
            ),
        ]
        return "insufficient_evidence", 0.2, comparisons, missing_data

    # Safe defaults for calculations
    loc = float(loc or 0)
    complexity_max = float(complexity_max or 0)
    coverage = float(coverage or 0)
    coupling = float(coupling or 0)
    god_classes = int(god_classes or 0)
    fixes = int(fixes or 0)

    # 1. Maintain Score
    # Favored when: low complexity (<10), low coupling (<4), low bug churn
    maintain_score = 90.0 - (complexity_max * 1.5) - (coupling * 3.0) - (fixes * 0.8) - (god_classes * 15.0)
    maintain_score = max(5.0, min(95.0, maintain_score))

    # 2. Refactor Score
    # Favored when: tests exist (>40% coverage), moderate complexity, high coupling or long methods
    refactor_score = 40.0 + (coverage * 0.4) - (complexity_max > 30 and 20.0 or 0.0) + (god_classes * 10.0)
    if coverage < 20.0:
        refactor_score -= 25.0  # Refactoring without safety net is dangerous
    refactor_score = max(5.0, min(95.0, refactor_score))

    # 3. Migrate Score
    # Favored when: zero tests, extreme complexity (>30), high coupling (>7), god classes, high bug fixes
    migrate_score = 20.0 + (complexity_max * 1.0) + (coupling * 4.0) + (god_classes * 12.0) + (fixes * 0.5)
    if coverage > 60.0 and complexity_max < 20:
        migrate_score -= 35.0  # Don't migrate healthy well-tested modules
    migrate_score = max(5.0, min(95.0, migrate_score))

    # Format Option Comparisons
    comparisons = [
        OptionComparison(
            option="maintain",
            score=round(maintain_score, 1),
            pros=["Zero migration risk", "Existing business logic remains untouched"],
            cons=["Accumulates technical debt if complexity increases"],
            rationale=f"Current max complexity is {complexity_max} with {fixes} bug fixes recorded."
        ),
        OptionComparison(
            option="refactor",
            score=round(refactor_score, 1),
            pros=["Preserves existing integrations", "Leverages existing test coverage"],
            cons=["Requires targeted code restructuring effort"],
            rationale=f"Test coverage is {coverage:.1f}% with coupling score of {coupling:.1f}."
        ),
        OptionComparison(
            option="migrate",
            score=round(migrate_score, 1),
            pros=["Eliminates architectural debt", "Allows modern framework adoption"],
            cons=["High development and QA cost", "Risk of regression on edge cases"],
            rationale=f"God classes detected: {god_classes}, coupling score: {coupling:.1f}."
        ),
    ]

    # Pick winner
    scored_sorted = sorted(comparisons, key=lambda x: x.score, reverse=True)
    winner = scored_sorted[0]

    # Calculate confidence based on evidence completeness
    confidence = 0.85
    if coverage == 0:
        confidence -= 0.15
    if fixes == 0:
        confidence -= 0.05
    confidence = round(max(0.4, confidence), 2)

    return winner.option, confidence, comparisons, missing_data
