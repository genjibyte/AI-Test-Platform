"""Landing-readiness Markdown presentation.

This renders an existing ``landing_readiness_snapshot.v1`` mapping for human
handoff. It does not compute readiness, read workspace state, persist labels,
materialize datasets, execute verifiers, or grant headline/verdict authority.
"""
from __future__ import annotations

from typing import Any, Mapping

from app.governance.landing_readiness import (
    LANDING_READINESS_BLOCKER_SUMMARY_VERSION,
    LANDING_READINESS_SNAPSHOT_VERSION,
    landing_readiness_blocker_summary,
    validate_landing_readiness_blocker_summary,
    validate_landing_readiness_snapshot,
)


def render_landing_readiness_markdown(snapshot: Mapping[str, Any]) -> str:
    """Render a landing-readiness snapshot, or ``""`` when absent."""
    if not isinstance(snapshot, Mapping):
        return ""
    if snapshot.get("schema_version") != LANDING_READINESS_SNAPSHOT_VERSION:
        return ""
    snapshot = validate_landing_readiness_snapshot(snapshot)

    lines = [
        "## Landing readiness - PLANNING SNAPSHOT",
        "",
        f"- schema_version: {_cell(snapshot.get('schema_version'))}",
        f"- overall_completion_percent: {snapshot.get('overall_completion_percent')}  "
        f"completion_band: {_cell(snapshot.get('completion_band'))}",
        f"- project_stage: {_cell(snapshot.get('project_stage'))}  "
        f"landing_stage: {_cell(snapshot.get('landing_stage'))}",
        f"- ready_for_80_stage: {snapshot.get('ready_for_80_stage')}  "
        f"ready_for_landing_claims: {snapshot.get('ready_for_landing_claims')}",
        f"- inputs: {_cell(snapshot.get('inputs') or {})}",
        f"- human_ready_metric_names: {_cell(snapshot.get('human_ready_metric_names') or [])}  "
        f"human_ready_metric_count: {snapshot.get('human_ready_metric_count')}",
        "- defect denominator: future_possible="
        f"{snapshot.get('future_defect_denominator_possible')}  "
        f"ready_now={snapshot.get('defect_denominator_ready_now')}",
        f"- source_versions: {_cell(snapshot.get('source_versions') or {})}",
        "- authority: headline_metric_authority="
        f"{snapshot.get('headline_metric_authority')}  "
        "dataset_materialization_allowed="
        f"{snapshot.get('dataset_materialization_allowed')}  "
        "verifier_execution_allowed="
        f"{snapshot.get('verifier_execution_allowed')}  "
        f"verdict_authority={snapshot.get('verdict_authority')}  "
        f"trusted_authority={snapshot.get('trusted_authority')}",
        "  (planning view only; no release, headline, dataset, verifier, verdict, or trust authority)",
        "",
        "| landing_blocker |",
        "|---|",
    ]
    blockers = snapshot.get("landing_blockers") or []
    if blockers:
        lines.extend(f"| {_cell(blocker)} |" for blocker in blockers)
    else:
        lines.append("| none |")

    lines += [
        "",
        "| next_best_step |",
        "|---|",
    ]
    steps = snapshot.get("next_best_steps") or []
    if steps:
        lines.extend(f"| {_cell(step)} |" for step in steps)
    else:
        lines.append("| none |")

    blocker_summary = landing_readiness_blocker_summary(snapshot)
    lines += [
        "",
        "| blocker_family | blocker_count | clearance_status | review_questions | evidence_items |",
        "|---|---:|---|---|---|",
    ]
    for family in blocker_summary.get("families") or []:
        lines.append(_blocker_family_row(family))

    lines += [
        "",
        "| review_question | triggered_by | authority |",
        "|---|---|---|",
    ]
    questions = snapshot.get("review_questions") or []
    if questions:
        lines.extend(_question_row(question) for question in questions)
    else:
        lines.append("| none | none | planning_only |")

    lines += [
        "",
        "| evidence_item | current_status | required_evidence | authority |",
        "|---|---|---|---|",
    ]
    checklist = snapshot.get("evidence_checklist") or []
    if checklist:
        lines.extend(_checklist_row(item) for item in checklist)
    else:
        lines.append("| none | none | none | planning_only |")

    lines.append("")
    return "\n".join(lines)


def render_landing_readiness_blocker_summary_markdown(
    summary: Mapping[str, Any],
) -> str:
    """Render a blocker-family summary, or ``""`` when absent."""
    if not isinstance(summary, Mapping):
        return ""
    if summary.get("schema_version") != LANDING_READINESS_BLOCKER_SUMMARY_VERSION:
        return ""
    summary = validate_landing_readiness_blocker_summary(summary)

    lines = [
        "## Landing readiness blocker summary - PLANNING VIEW",
        "",
        f"- schema_version: {_cell(summary.get('schema_version'))}",
        f"- source_schema_version: {_cell(summary.get('source_schema_version'))}",
        f"- landing_stage: {_cell(summary.get('landing_stage'))}  "
        f"ready_for_80_stage: {summary.get('ready_for_80_stage')}  "
        f"ready_for_landing_claims: {summary.get('ready_for_landing_claims')}",
        f"- total_blockers: {summary.get('total_blockers')}  "
        f"next_clearance_family: {_cell(summary.get('next_clearance_family'))}",
        f"- family_counts: {_cell(summary.get('family_counts') or {})}",
        f"- evidence_status_counts: {_cell(summary.get('evidence_status_counts') or {})}",
        "- authority: headline_metric_authority="
        f"{summary.get('headline_metric_authority')}  "
        "dataset_materialization_allowed="
        f"{summary.get('dataset_materialization_allowed')}  "
        "verifier_execution_allowed="
        f"{summary.get('verifier_execution_allowed')}  "
        f"verdict_authority={summary.get('verdict_authority')}  "
        f"trusted_authority={summary.get('trusted_authority')}",
        "  (planning view only; no source recompute, evidence collection, release, headline, verdict, or trust authority)",
        "",
        "| blocker_family | blocker_count | clearance_status | review_questions | evidence_items |",
        "|---|---:|---|---|---|",
    ]
    for family in summary.get("families") or []:
        lines.append(_blocker_family_row(family))
    lines.append("")
    return "\n".join(lines)


def _blocker_family_row(family: Mapping[str, Any]) -> str:
    return (
        f"| {_cell(family.get('family'))} "
        f"| {family.get('blocker_count')} "
        f"| {_cell(family.get('clearance_status'))} "
        f"| {_cell(family.get('review_question_ids') or [])} "
        f"| {_cell(family.get('non_present_evidence_item_ids') or [])} |"
    )


def _question_row(question: Any) -> str:
    if not isinstance(question, Mapping):
        return f"| {_cell(question)} | none | planning_only |"
    return (
        f"| {_cell(question.get('question'))} "
        f"| {_cell(question.get('triggered_by') or [])} "
        f"| {_cell(question.get('authority'))} |"
    )


def _checklist_row(item: Any) -> str:
    if not isinstance(item, Mapping):
        return f"| {_cell(item)} | unknown | unknown | planning_only |"
    return (
        f"| {_cell(item.get('id'))} "
        f"| {_cell(item.get('current_status'))} "
        f"| {_cell(item.get('required_evidence'))} "
        f"| {_cell(item.get('authority'))} |"
    )


def _cell(value: Any) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = ", ".join(f"{key}={item}" for key, item in value.items())
    else:
        text = "" if value is None else str(value)
    return text.replace("|", "/").replace("\n", " ").strip()
