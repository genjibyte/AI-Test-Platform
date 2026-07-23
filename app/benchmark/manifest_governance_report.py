"""Golden Set manifest governance presentation.

This renders the S5B metadata-only governance plan for humans. It is not wired
into benchmark reports by default and does not change aggregate metrics,
manifest pins, ledger records, executors, digest severity, or verdicts.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.benchmark.manifest_governance import golden_manifest_governance_plan


def render_golden_manifest_governance_markdown(
    records: Iterable[Mapping[str, Any]],
) -> str:
    """Render a Golden Set manifest-seed governance plan as Markdown.

    Empty input renders an empty string so callers can opt in without adding
    noise when no external manifest seeds are under review.
    """
    plan = golden_manifest_governance_plan(records)
    if plan.get("total_records", 0) <= 0:
        return ""

    lines: list[str] = [
        "## Golden Set manifest governance - METADATA PLAN",
        "",
        f"- total_records: {plan.get('total_records')}  "
        f"seed_schema_version: {plan.get('seed_schema_version')}",
        f"- metadata_only_records: {plan.get('metadata_only_records')}",
        f"- golden_manifest_draft_records: {plan.get('golden_manifest_draft_records')}",
        f"- small_seed_policy_ok_records: {plan.get('small_seed_policy_ok_records')}",
        f"- large_seed_request_records: {plan.get('large_seed_request_records')}",
        f"- future_owner_gated_records: {plan.get('future_owner_gated_records')}",
        f"- runtime_risk_records: {plan.get('runtime_risk_records')}",
        f"- by_candidate_kind: {plan.get('by_candidate_kind')}",
        f"- by_project_artifact: {plan.get('by_project_artifact')}",
        "- authority: runtime_actions_allowed_records="
        f"{plan.get('runtime_actions_allowed_records')}  "
        f"download_allowed_records={plan.get('download_allowed_records')}  "
        f"install_allowed_records={plan.get('install_allowed_records')}  "
        "benchmark_headline_allowed_records="
        f"{plan.get('benchmark_headline_allowed_records')}  "
        f"verdict_authority_records={plan.get('verdict_authority_records')}",
        "  (metadata only; no dataset slice, execution, headline metric, or verdict authority)",
        "",
        "| asset_id | candidate_kind | tasks | future_owner_gate_reasons | runtime_flags | project_artifact |",
        "|---|---|---:|---|---|---|",
    ]
    for record in plan.get("records", []):
        lines.append(_record_row(record))
    lines.append("")
    return "\n".join(lines)


def _record_row(record: Mapping[str, Any]) -> str:
    runtime_flags = [
        name
        for name in (
            "requires_network",
            "requires_docker",
            "requires_model_or_api_key",
        )
        if record.get(name) is True
    ]
    return (
        f"| {_cell(record.get('asset_id'))} "
        f"| {_cell(record.get('candidate_kind'))} "
        f"| {record.get('task_count_requested')} "
        f"| {_cell(record.get('future_owner_gate_reasons') or [])} "
        f"| {_cell(runtime_flags or ['none'])} "
        f"| {_cell(record.get('project_artifact'))} |"
    )


def _cell(value: Any) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    else:
        text = "" if value is None else str(value)
    return text.replace("|", "/").replace("\n", " ").strip()
