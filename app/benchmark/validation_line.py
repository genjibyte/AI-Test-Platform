"""Real-world validation-line metrics (docs/50_benchmark/56).

Pure projections over ``BenchCaseResult`` rows. These helpers do not change judging,
recommendations, aggregate headline keys, ledger schema, or report conclusions.
"""
from __future__ import annotations

from typing import Iterable, Optional

from app.benchmark.models import BenchCaseResult

FIRST_COMPILED_OUTCOMES = {"PASS", "TEST_FAILURE", "NO_TESTS"}
WEAK_QUALITY_CODES = {
    "no_assertions",
    "only_weak_assertions",
    "weak_assertion_heavy",
    "tautological_assertion",
}
WEAK_ORACLE_STRENGTHS = {"none", "weak", "mixed"}

HUMAN_OR_GOLDEN_METRICS = {
    "usable_test_rate": "requires_human_disposition_labels",
    "defect_discovery_rate": "requires_pinned_defect_or_seeded_defect_verifier",
    "human_edit_count": "requires_human_review_edit_annotations",
    "human_handling_time": "requires_human_review_timestamps",
    "diagnosis_time": "requires_human_or_verifier_rca_timestamps",
    "misjudgment_rate": "requires_human_or_golden_reference_labels",
}


def _rate(total: int, count: int) -> Optional[float]:
    if total <= 0:
        return None
    return round(count / total, 4)


def _filtered(
    cases: Iterable[BenchCaseResult],
    *,
    run_kind: Optional[str],
) -> list[BenchCaseResult]:
    rows = list(cases)
    if run_kind is None:
        return rows
    return [c for c in rows if c.run_kind == run_kind]


def _first_run_evidence(cases: Iterable[BenchCaseResult]) -> list[BenchCaseResult]:
    """Rows with unambiguous first-run execution facts.

    When repair rounds were applied, the row's final outcome may no longer be the first-run
    outcome. Until first-run evidence is persisted separately, exclude those rows from first-pass
    denominators instead of over-claiming.
    """
    return [
        c
        for c in cases
        if c.repo_judged
        and c.gen_outcome is not None
        and not ((c.repair_rounds or 0) > 0)
    ]


def _review_quality_codes(case: BenchCaseResult) -> set[str]:
    quality = (case.review_summary or {}).get("quality") if case.review_summary else None
    if not isinstance(quality, dict):
        return set()
    codes = set(quality.get("blockers") or [])
    codes |= set(quality.get("warnings") or [])
    return {str(c) for c in codes if c}


def _oracle_strength(case: BenchCaseResult) -> Optional[str]:
    if case.oracle_strength:
        return case.oracle_strength
    estimate = (
        (case.review_summary or {}).get("oracle_strength_estimate")
        if case.review_summary else None
    )
    if isinstance(estimate, dict):
        value = estimate.get("oracle_strength")
        return str(value) if value is not None else None
    return None


def _weak_mutation_signal(case: BenchCaseResult) -> bool:
    survivors = (
        (case.review_summary or {}).get("mutation_survivors")
        if case.review_summary else None
    )
    if not isinstance(survivors, dict):
        return False
    counts = survivors.get("counts") or {}
    try:
        return int(counts.get("survived_weak_oracle") or 0) > 0
    except (TypeError, ValueError):
        return False


def _has_structural_weak_signal(case: BenchCaseResult) -> bool:
    if _review_quality_codes(case) & WEAK_QUALITY_CODES:
        return True
    if (_oracle_strength(case) or "").lower() in WEAK_ORACLE_STRENGTHS:
        return True
    return _weak_mutation_signal(case)


def _has_quality_evidence(case: BenchCaseResult) -> bool:
    return (
        case.quality_gate_status is not None
        or bool(_review_quality_codes(case))
        or _oracle_strength(case) is not None
        or _weak_mutation_signal(case)
    )


def _preflight_rejected(case: BenchCaseResult) -> bool:
    preflight = (
        (case.review_summary or {}).get("preflight")
        if case.review_summary else None
    )
    return isinstance(preflight, dict) and preflight.get("status") == "FAIL"


def validation_line_summary(
    cases: Iterable[BenchCaseResult],
    *,
    run_kind: Optional[str] = None,
) -> dict:
    """Return the V1 real-world validation-line summary over existing benchmark rows.

    V1 is intentionally limited to automated evidence that already exists: first compile pass,
    first test pass, and structural weak-signal rate. Human/golden metrics are surfaced as
    unavailable with explicit requirements.
    """
    rows = _filtered(cases, run_kind=run_kind)
    first_rows = _first_run_evidence(rows)
    quality_rows = [c for c in first_rows if _has_quality_evidence(c)]

    first_compile_count = sum(
        1 for c in first_rows if c.gen_outcome in FIRST_COMPILED_OUTCOMES
    )
    first_test_pass_count = sum(1 for c in first_rows if c.gen_outcome == "PASS")
    weak_count = sum(1 for c in quality_rows if _has_structural_weak_signal(c))
    repaired_ambiguous = sum(
        1 for c in rows if c.repo_judged and c.gen_outcome is not None and (c.repair_rounds or 0) > 0
    )

    return {
        "run_kind_filter": run_kind,
        "total_cases": len(rows),
        "generation_attempted": sum(1 for c in rows if c.repo_judged),
        "first_run_evidence_cases": len(first_rows),
        "first_run_ambiguous_due_to_repair": repaired_ambiguous,
        "preflight_reject_cases": sum(1 for c in rows if _preflight_rejected(c)),
        "first_compile_pass_count": first_compile_count,
        "first_compile_pass_rate": _rate(len(first_rows), first_compile_count),
        "first_test_pass_count": first_test_pass_count,
        "first_test_pass_rate": _rate(len(first_rows), first_test_pass_count),
        "structural_weak_signal_evaluated_cases": len(quality_rows),
        "structural_weak_signal_cases": weak_count,
        "structural_weak_signal_rate": _rate(len(quality_rows), weak_count),
        "human_or_golden_metrics": {
            name: {"value": None, "status": status}
            for name, status in HUMAN_OR_GOLDEN_METRICS.items()
        },
        "note": (
            "V1 uses automated judge evidence only; usable/defect/human-time/"
            "diagnosis/misjudgment metrics require human or golden labels."
        ),
    }
