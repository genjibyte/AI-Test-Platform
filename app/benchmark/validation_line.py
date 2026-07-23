"""Real-world validation-line metrics (docs/50_benchmark/56).

Pure projections over ``BenchCaseResult`` rows. These helpers do not change judging,
recommendations, aggregate headline keys, ledger schema, or report conclusions.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from app.benchmark.models import BenchCaseResult
from app.review.human_labels import (
    METRIC_PROJECTION_VERSION,
    label_metric_projection,
)

HUMAN_LABEL_READINESS_VERSION = "human_label_metric_readiness.v1"

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


def human_label_metric_readiness(
    labels_or_projections: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize whether human/golden labels are sufficient for landing metrics.

    This helper is pure and non-persistent. It does not compute benchmark
    headline metrics, change aggregates, or treat labels as acceptance commands.
    """
    projections = [_as_metric_projection(item) for item in labels_or_projections]
    reviewed = [item for item in projections if item.get("human_reviewed") is True]
    dispositions = [
        item for item in reviewed if item.get("disposition") is not None
    ]
    timed = [
        item for item in reviewed
        if item.get("human_handling_time_seconds") is not None
    ]
    root_cause_recorded = [
        item for item in reviewed if item.get("root_cause_recorded") is True
    ]
    misjudgment_labeled = [
        item for item in reviewed if item.get("misjudgment_kind") is not None
    ]
    defect_labels = [
        item for item in reviewed if item.get("defect_discovery_label") is True
    ]

    usable_count = sum(1 for item in dispositions if item.get("usable_test") is True)
    revision_counts = [
        int(item.get("manual_revision_count") or 0)
        for item in dispositions
    ]
    misjudgment_count = sum(
        1
        for item in misjudgment_labeled
        if item.get("misjudgment_kind") not in (None, "none")
    )

    return {
        "schema_version": HUMAN_LABEL_READINESS_VERSION,
        "advisory": True,
        "report_only": True,
        "total_label_rows": len(projections),
        "human_reviewed_rows": len(reviewed),
        "metrics": {
            "usable_test_rate": {
                "status": _available_if(dispositions, "requires_human_disposition_labels"),
                "denominator": len(dispositions),
                "numerator": usable_count,
                "value": _rate(len(dispositions), usable_count),
                "headline_allowed_now": False,
            },
            "human_edit_count": {
                "status": _available_if(dispositions, "requires_human_review_edit_annotations"),
                "denominator": len(dispositions),
                "average_manual_revision_count": _average(revision_counts),
                "headline_allowed_now": False,
            },
            "human_handling_time": {
                "status": _available_if(timed, "requires_human_review_timestamps"),
                "denominator": len(timed),
                "average_seconds": _average([
                    int(item["human_handling_time_seconds"])
                    for item in timed
                ]),
                "headline_allowed_now": False,
            },
            "diagnosis_time": {
                "status": (
                    "rca_labels_present_but_requires_failure_first_surfaced_timestamp"
                    if root_cause_recorded
                    else "requires_human_or_verifier_rca_timestamps"
                ),
                "root_cause_recorded_rows": len(root_cause_recorded),
                "value": None,
                "headline_allowed_now": False,
            },
            "misjudgment_rate": {
                "status": _available_if(
                    misjudgment_labeled,
                    "requires_human_or_golden_reference_labels",
                ),
                "denominator": len(misjudgment_labeled),
                "numerator": misjudgment_count,
                "value": _rate(len(misjudgment_labeled), misjudgment_count),
                "headline_allowed_now": False,
            },
            "defect_discovery_rate": {
                "status": (
                    "defect_labels_present_but_requires_pinned_defect_denominator"
                    if defect_labels
                    else "requires_pinned_defect_or_seeded_defect_verifier"
                ),
                "defect_discovery_label_count": len(defect_labels),
                "value": None,
                "headline_allowed_now": False,
            },
        },
        "ready_metric_count": sum(
            1
            for metric in ("usable_test_rate", "human_edit_count", "human_handling_time", "misjudgment_rate")
            if (
                (metric == "usable_test_rate" and dispositions)
                or (metric == "human_edit_count" and dispositions)
                or (metric == "human_handling_time" and timed)
                or (metric == "misjudgment_rate" and misjudgment_labeled)
            )
        ),
        "not_ready_reasons": _label_not_ready_reasons(
            dispositions=dispositions,
            timed=timed,
            root_cause_recorded=root_cause_recorded,
            misjudgment_labeled=misjudgment_labeled,
            defect_labels=defect_labels,
        ),
        "runtime_authority": False,
        "persistence_authority": False,
        "headline_metric_authority": False,
        "digest_authority": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "note": (
            "Human/golden labels can make landing metrics computable, but this "
            "readiness summary does not approve headline claims, persistence, "
            "verdict changes, or trusted=True."
        ),
    }


def _as_metric_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise TypeError("label rows must be mappings")
    if item.get("schema_version") == METRIC_PROJECTION_VERSION:
        return dict(item)
    return label_metric_projection(dict(item))


def _available_if(rows: list[dict[str, Any]], unavailable_status: str) -> str:
    return "available_from_supplied_labels" if rows else unavailable_status


def _average(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _label_not_ready_reasons(
    *,
    dispositions: list[dict[str, Any]],
    timed: list[dict[str, Any]],
    root_cause_recorded: list[dict[str, Any]],
    misjudgment_labeled: list[dict[str, Any]],
    defect_labels: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    if not dispositions:
        reasons.append("human_disposition_labels_missing")
    if not timed:
        reasons.append("human_review_timestamps_missing")
    if not root_cause_recorded:
        reasons.append("root_cause_timestamps_missing")
    else:
        reasons.append("failure_first_surfaced_timestamp_missing_for_diagnosis_time")
    if not misjudgment_labeled:
        reasons.append("misjudgment_reference_labels_missing")
    if defect_labels:
        reasons.append("pinned_defect_denominator_missing")
    else:
        reasons.append("defect_verifier_or_product_bug_labels_missing")
    return reasons
