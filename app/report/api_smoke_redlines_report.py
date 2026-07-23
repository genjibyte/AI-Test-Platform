"""Markdown rendering for API smoke red-line summaries.

Presentation only: renders an existing ``review_summary["api_smoke_redlines"]``
block for human handoff. It does not compute eligibility, run executors, write
benchmark/ledger records, feed digest, or change verdict authority.
"""
from __future__ import annotations

from typing import Any, Mapping


def render_api_smoke_redlines_markdown(review_summary: Mapping[str, Any]) -> str:
    """Render the API smoke red-line summary, or ``""`` when absent."""
    if not isinstance(review_summary, Mapping):
        return ""
    summary = review_summary.get("api_smoke_redlines")
    if not isinstance(summary, Mapping):
        return ""

    lines = [
        "## API smoke red lines - REPORT ONLY",
        "",
        f"- summary_version: {_cell(summary.get('summary_version'))}",
        f"- candidate_kind: {_cell(summary.get('candidate_kind') or 'unknown')}  "
        f"smoke_id: {_cell(summary.get('smoke_id') or 'unknown')}",
        f"- evidence_present: {summary.get('api_evidence_present')}  "
        f"manifest_present: {summary.get('api_smoke_manifest_present')}  "
        f"denominator_present: {summary.get('api_smoke_denominator_present')}",
        f"- redlines_satisfied: {summary.get('redlines_satisfied')}  "
        f"digest_signal: {summary.get('digest_signal')}",
        f"- review_flags: {_cell(summary.get('review_flags') or [])}",
        "- authority: verdict_authority="
        f"{summary.get('verdict_authority')}  "
        f"trusted_authority={summary.get('trusted_authority')}",
        "  (review prompt only; no executor, digest, benchmark/ledger, or verdict change)",
        "",
        "| boundary | facts |",
        "|---|---|",
        f"| redaction | {_boundary(summary.get('redaction'))} |",
        f"| execution | {_boundary(summary.get('execution_boundary'))} |",
        f"| authority | {_boundary(summary.get('authority_boundary'))} |",
        "",
    ]
    return "\n".join(lines)


def _boundary(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    return ", ".join(
        f"{_cell(key)}={_cell(item)}"
        for key, item in value.items()
    )


def _cell(value: Any) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    else:
        text = "" if value is None else str(value)
    return text.replace("|", "/").replace("\n", " ").strip()
