"""API smoke ledger presentation (docs/50_benchmark/60 S10C).

This renders the named S10B projection for humans. It is presentation only:
no existing ledger analytics, retrieval, badcase signatures, SQLite schema,
digest severity, executor behavior, or verdicts are changed here.
"""
from __future__ import annotations

from typing import Iterable

from app.ledger.api_smoke_projection import api_smoke_ledger_projection
from app.ledger.models import JudgedRecord


def render_api_smoke_ledger_markdown(records: Iterable[JudgedRecord]) -> str:
    """Render API smoke ledger RAW + separate HEADLINE sections.

    Ordinary unit-test ledgers with no S10A carry render as an empty string so
    callers can opt in without adding noise to existing reports.
    """
    all_records = list(records)
    raw = api_smoke_ledger_projection(all_records)
    if raw.get("api_smoke_source_records", 0) <= 0:
        return ""

    headline = api_smoke_ledger_projection(all_records, view="headline")
    lines: list[str] = []
    lines += _projection_lines(
        raw,
        "API smoke ledger - RAW (all run_kinds)",
        "advisory; separate from existing ledger analytics and badcase signatures",
    )
    lines += _projection_lines(
        headline,
        "API smoke ledger - HEADLINE (S8 eligible; real/external only)",
        "candidate-evaluation view; not value proof or adoption evidence",
    )
    return "\n".join(lines)


def _projection_lines(summary: dict, title: str, footer: str) -> list[str]:
    return [
        f"## {title}",
        "",
        f"- source_records: {summary.get('api_smoke_source_records')}  "
        f"projected_records: {summary.get('projected_records')}  "
        f"(run_kind_filter: {summary.get('run_kind_filter')})",
        f"- eligible_source_records: {summary.get('eligible_source_records')}  "
        f"ineligible_source_records: {summary.get('ineligible_source_records')}",
        f"- by_run_kind: {summary.get('by_run_kind')}",
        f"- by_smoke_id: {summary.get('by_smoke_id')}",
        f"- by_candidate_kind: {summary.get('by_candidate_kind')}",
        f"- not_eligible_reason_counts: {summary.get('not_eligible_reason_counts')}",
        f"- requirement_failure_counts: {summary.get('requirement_failure_counts')}",
        f"- gen_outcome_distribution: {summary.get('gen_outcome_distribution')}",
        f"- quality_gate_distribution: {summary.get('quality_gate_distribution')}",
        "- review_recommendation_distribution: "
        f"{summary.get('review_recommendation_distribution')}",
        f"- need_human_review_records: {summary.get('need_human_review_records')}  "
        "benchmark_counting_enabled_records: "
        f"{summary.get('benchmark_counting_enabled_records')}  "
        "unit_headline_eligible_records: "
        f"{summary.get('unit_headline_eligible_records')}",
        f"- invariant_warnings: {summary.get('invariant_warnings')}",
        f"  ({footer})",
        "",
    ]
