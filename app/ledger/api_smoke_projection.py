"""API smoke ledger projection (docs/50_benchmark/60 S10B).

Pure descriptive counts over compact S10A ``JudgedRecord`` JSON carry fields.
This module does not change ledger_summary, badcase signatures, retrieval,
SQLite schemas, executors, digest severity, or verdicts.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from app.ledger.models import JudgedRecord

PROJECTION_VERSION = "api_smoke_ledger_projection.v1"
SOURCE_POLICY_VERSION = "api_smoke_denominator.v1"
SOURCE_SCOPE = "separate_api_smoke_denominator"
HEADLINE_RUN_KINDS = frozenset({"real", "external"})


def api_smoke_ledger_projection(
    records: Iterable[JudgedRecord],
    *,
    view: str = "raw",
) -> dict[str, Any]:
    """Return the S10B API smoke projection over ledger records.

    ``raw`` includes every ledger record with valid S10A carry. ``headline`` is
    a separate API-smoke candidate-evaluation view: S8-eligible records with
    top-level ``run_kind`` in ``{"real", "external"}``. It is not the existing
    unit-test model-quality headline, which remains ``run_kind == "real"`` only.
    """
    if view not in {"raw", "headline"}:
        raise ValueError("view must be 'raw' or 'headline'")

    all_records = list(records)
    sources = [record for record in all_records if _is_api_smoke_source(record)]
    projected = _projected_records(sources, view=view)
    invariant_warnings = _invariant_warnings(projected)

    return {
        "projection_version": PROJECTION_VERSION,
        "view": view,
        "source_policy_version": SOURCE_POLICY_VERSION,
        "source_scope": SOURCE_SCOPE,
        "run_kind_filter": None if view == "raw" else sorted(HEADLINE_RUN_KINDS),
        "total_records_seen": len(all_records),
        "api_smoke_source_records": len(sources),
        "projected_records": len(projected),
        "eligible_source_records": _eligible_count(sources),
        "ineligible_source_records": len(sources) - _eligible_count(sources),
        "eligible_projected_records": _eligible_count(projected),
        "ineligible_projected_records": len(projected) - _eligible_count(projected),
        "by_run_kind": _counter_dict(_bucket(record.run_kind) for record in projected),
        "by_candidate_kind": _counter_dict(
            _bucket(record.api_smoke_candidate_kind) for record in projected
        ),
        "by_smoke_id": _counter_dict(
            _bucket(record.api_smoke_smoke_id) for record in projected
        ),
        "not_eligible_reason_counts": _counter_dict(
            reason
            for record in projected
            for reason in record.api_smoke_not_eligible_reasons
        ),
        "requirement_failure_counts": _counter_dict(
            name
            for record in projected
            for name in record.api_smoke_requirement_failures
        ),
        "gen_outcome_distribution": _counter_dict(
            _bucket(record.gen_outcome) for record in projected
        ),
        "quality_gate_distribution": _counter_dict(
            _bucket(record.quality_gate_status) for record in projected
        ),
        "review_recommendation_distribution": _counter_dict(
            _bucket(record.review_recommendation) for record in projected
        ),
        "need_human_review_records": sum(
            1 for record in projected if record.conclusion == "NEED_HUMAN_REVIEW"
        ),
        "benchmark_counting_enabled_records": sum(
            1 for record in projected if record.api_smoke_benchmark_counting_enabled is True
        ),
        "unit_headline_eligible_records": sum(
            1 for record in projected if record.api_smoke_unit_headline_eligible is True
        ),
        "invariant_warnings": invariant_warnings,
        "note": _note(view),
    }


def _is_api_smoke_source(record: JudgedRecord) -> bool:
    return (
        record.api_smoke_policy_version == SOURCE_POLICY_VERSION
        and record.api_smoke_scope == SOURCE_SCOPE
    )


def _projected_records(
    sources: list[JudgedRecord],
    *,
    view: str,
) -> list[JudgedRecord]:
    if view == "raw":
        return sources
    return [
        record
        for record in sources
        if record.api_smoke_denominator_eligible is True
        and record.run_kind in HEADLINE_RUN_KINDS
    ]


def _eligible_count(records: list[JudgedRecord]) -> int:
    return sum(
        1 for record in records if record.api_smoke_denominator_eligible is True
    )


def _invariant_warnings(records: list[JudgedRecord]) -> list[str]:
    warnings: list[str] = []
    if any(record.api_smoke_benchmark_counting_enabled is True for record in records):
        warnings.append("api_smoke_row_marked_benchmark_counting_enabled")
    if any(record.api_smoke_unit_headline_eligible is True for record in records):
        warnings.append("api_smoke_row_marked_unit_headline_eligible")
    if any(record.conclusion != "NEED_HUMAN_REVIEW" for record in records):
        warnings.append("api_smoke_row_not_need_human_review")
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
            "RAW includes all API smoke ledger carry records; advisory only and "
            "separate from existing ledger analytics."
        )
    return (
        "API smoke ledger HEADLINE includes S8-eligible real/external records "
        "only; candidate-evaluation view, not model-quality or auto-accept evidence."
    )
