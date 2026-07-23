"""API smoke benchmark projection (docs/50_benchmark/59).

Pure descriptive counts over S8 ``review_summary["api_smoke_denominator"]``
facts. This module does not change aggregate metrics, ledger records, report
verdicts, executors, or digest severity.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from app.benchmark.models import BenchCaseResult
from app.report.api_smoke_redlines import REDLINE_SUMMARY_VERSION

PROJECTION_VERSION = "api_smoke_benchmark_projection.v1"
SOURCE_POLICY_VERSION = "api_smoke_denominator.v1"
SOURCE_SCOPE = "separate_api_smoke_denominator"
HEADLINE_RUN_KINDS = frozenset({"real", "external"})


def api_smoke_benchmark_projection(
    cases: Iterable[BenchCaseResult],
    *,
    view: str = "raw",
) -> dict[str, Any]:
    """Return the S9A API smoke projection over benchmark rows.

    ``raw`` includes every valid S8 denominator source row. ``headline`` is a
    separate API-smoke candidate-evaluation view: S8-eligible rows with
    ``run_kind`` in ``{"real", "external"}``. It is not the existing unit-test
    model-quality headline, which remains ``run_kind == "real"`` only.
    """
    if view not in {"raw", "headline"}:
        raise ValueError("view must be 'raw' or 'headline'")

    all_cases = list(cases)
    sources = [
        (case, denominator)
        for case in all_cases
        if (denominator := _api_smoke_denominator(case)) is not None
    ]
    projected = _projected_rows(sources, view=view)
    invariant_warnings = _invariant_warnings(projected)

    return {
        "projection_version": PROJECTION_VERSION,
        "view": view,
        "source_policy_version": SOURCE_POLICY_VERSION,
        "source_scope": SOURCE_SCOPE,
        "run_kind_filter": None if view == "raw" else sorted(HEADLINE_RUN_KINDS),
        "total_cases_seen": len(all_cases),
        "api_smoke_source_rows": len(sources),
        "projected_rows": len(projected),
        "eligible_source_rows": _eligible_count(sources),
        "ineligible_source_rows": len(sources) - _eligible_count(sources),
        "eligible_projected_rows": _eligible_count(projected),
        "ineligible_projected_rows": len(projected) - _eligible_count(projected),
        "by_run_kind": _counter_dict(_run_kind(case) for case, _ in projected),
        "by_candidate_kind": _counter_dict(
            _bucket(denominator.get("candidate_kind")) for _, denominator in projected
        ),
        "by_smoke_id": _counter_dict(
            _bucket(denominator.get("smoke_id")) for _, denominator in projected
        ),
        "not_eligible_reason_counts": _counter_dict(
            reason
            for _, denominator in projected
            for reason in _reason_values(denominator)
        ),
        "requirement_failure_counts": _counter_dict(
            name
            for _, denominator in projected
            for name in _failed_requirement_names(denominator)
        ),
        "redline_flag_counts": _counter_dict(
            flag
            for case, _ in projected
            for flag in _redline_flag_values(case)
        ),
        "redlines_satisfied_distribution": _counter_dict(
            _redlines_satisfied_bucket(case) for case, _ in projected
        ),
        "gen_outcome_distribution": _counter_dict(
            _bucket(case.gen_outcome) for case, _ in projected
        ),
        "quality_gate_distribution": _counter_dict(
            _bucket(case.quality_gate_status) for case, _ in projected
        ),
        "review_recommendation_distribution": _counter_dict(
            _bucket(case.review_recommendation) for case, _ in projected
        ),
        "need_human_review_cases": sum(
            1 for case, _ in projected if case.conclusion == "NEED_HUMAN_REVIEW"
        ),
        "trusted_true_cases": sum(
            1
            for _, denominator in projected
            if _requirements(denominator).get("trusted_false") is False
        ),
        "unit_headline_eligible_cases": sum(
            1 for _, denominator in projected if denominator.get("unit_headline_eligible") is True
        ),
        "invariant_warnings": invariant_warnings,
        "note": _note(view),
    }


def _projected_rows(
    sources: list[tuple[BenchCaseResult, Mapping[str, Any]]],
    *,
    view: str,
) -> list[tuple[BenchCaseResult, Mapping[str, Any]]]:
    if view == "raw":
        return sources
    return [
        (case, denominator)
        for case, denominator in sources
        if denominator.get("eligible_for_api_smoke_denominator") is True
        and _run_kind(case) in HEADLINE_RUN_KINDS
    ]


def _api_smoke_denominator(case: BenchCaseResult) -> Mapping[str, Any] | None:
    review_summary = case.review_summary or {}
    if not isinstance(review_summary, Mapping):
        return None
    denominator = review_summary.get("api_smoke_denominator")
    if not isinstance(denominator, Mapping):
        return None
    if denominator.get("policy_version") != SOURCE_POLICY_VERSION:
        return None
    if denominator.get("scope") != SOURCE_SCOPE:
        return None
    return denominator


def _eligible_count(rows: list[tuple[BenchCaseResult, Mapping[str, Any]]]) -> int:
    return sum(
        1
        for _, denominator in rows
        if denominator.get("eligible_for_api_smoke_denominator") is True
    )


def _run_kind(case: BenchCaseResult) -> str:
    return _bucket(case.run_kind)


def _requirements(denominator: Mapping[str, Any]) -> Mapping[str, Any]:
    requirements = denominator.get("requirements")
    return requirements if isinstance(requirements, Mapping) else {}


def _failed_requirement_names(denominator: Mapping[str, Any]) -> list[str]:
    return [
        str(name)
        for name, value in _requirements(denominator).items()
        if value is not True
    ]


def _reason_values(denominator: Mapping[str, Any]) -> list[str]:
    reasons = denominator.get("not_eligible_reasons")
    if not isinstance(reasons, list):
        return []
    return [str(reason) for reason in reasons if reason]


def _api_smoke_redlines(case: BenchCaseResult) -> Mapping[str, Any] | None:
    review_summary = case.review_summary or {}
    if not isinstance(review_summary, Mapping):
        return None
    redlines = review_summary.get("api_smoke_redlines")
    if not isinstance(redlines, Mapping):
        return None
    if redlines.get("summary_version") != REDLINE_SUMMARY_VERSION:
        return None
    return redlines


def _redline_flag_values(case: BenchCaseResult) -> list[str]:
    redlines = _api_smoke_redlines(case)
    if redlines is None:
        return []
    flags = redlines.get("review_flags")
    if not isinstance(flags, list):
        return []
    return [str(flag) for flag in flags if flag]


def _redlines_satisfied_bucket(case: BenchCaseResult) -> str:
    redlines = _api_smoke_redlines(case)
    if redlines is None:
        return "absent"
    value = redlines.get("redlines_satisfied")
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def _invariant_warnings(rows: list[tuple[BenchCaseResult, Mapping[str, Any]]]) -> list[str]:
    warnings: list[str] = []
    if any(denominator.get("unit_headline_eligible") is True for _, denominator in rows):
        warnings.append("api_smoke_row_marked_unit_headline_eligible")
    if any(_requirements(denominator).get("trusted_false") is False for _, denominator in rows):
        warnings.append("api_smoke_row_not_trusted_false")
    return warnings


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values).most_common())


def _bucket(value: Any) -> str:
    if value is None or value == "":
        return "unknown"
    return str(value)


def _note(view: str) -> str:
    if view == "raw":
        return (
            "RAW includes all API smoke denominator rows; advisory only and not a "
            "generic aggregate headline."
        )
    return (
        "API smoke HEADLINE includes S8-eligible real/external rows only; "
        "candidate-evaluation view, not model-quality or auto-accept evidence."
    )
