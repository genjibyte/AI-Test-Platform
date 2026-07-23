"""Report-only API smoke denominator policy (docs/60_api_candidate/09).

This module computes eligibility facts for a future separate API-smoke
denominator. It does not count benchmark rows, write ledger records, render
markdown, start executors, or change verdicts.
"""
from __future__ import annotations

from typing import Any, Mapping

from app.report.api_evidence import JUNIT_API_CANDIDATE

POLICY_VERSION = "api_smoke_denominator.v1"
SCOPE = "separate_api_smoke_denominator"
ALLOWED_MANIFEST_STATUSES = {"approved", "active"}


def evaluate_api_smoke_denominator(
    review_summary: Mapping[str, Any],
    *,
    run_kind: str | None,
    execution: Mapping[str, Any] | None,
    conclusion: str,
    trusted: bool,
) -> dict[str, Any] | None:
    """Return a report-only denominator eligibility block when a manifest exists.

    Eligibility means the row has the local facts a later benchmark design would
    need for a separate API-smoke denominator. It is not a correctness claim, and
    benchmark counting remains disabled here.
    """
    manifest = _optional_mapping(review_summary.get("api_smoke_manifest"))
    if not manifest:
        return None

    alignment = _optional_mapping(manifest.get("alignment")) or {}
    execution = execution or {}

    api_evidence_present = alignment.get("api_evidence_present") is True
    requirements = {
        "manifest_present": True,
        "manifest_status_allowed": manifest.get("status") in ALLOWED_MANIFEST_STATUSES,
        "candidate_kind_matches": (
            manifest.get("candidate_kind") == JUNIT_API_CANDIDATE
            and alignment.get("candidate_kind_matches") is True
        ),
        "target_matches_generation": (
            alignment.get("target_matches_generation") is True
        ),
        "api_evidence_present": api_evidence_present,
        "api_evidence_candidate_kind_matches": (
            alignment.get("api_evidence_candidate_kind_matches")
            if api_evidence_present else None
        ),
        "runner_tool_matches": (
            alignment.get("runner_tool_matches") if api_evidence_present else None
        ),
        "redaction_contract_satisfied": (
            alignment.get("redaction_contract_satisfied")
            if api_evidence_present else None
        ),
        "maven_judge_evidence_present": bool(execution.get("gen_outcome")),
        "conclusion_needs_review": conclusion == "NEED_HUMAN_REVIEW",
        "trusted_false": trusted is False,
    }
    reasons = _not_eligible_reasons(requirements)

    return {
        "advisory": True,
        "report_only": True,
        "policy_version": POLICY_VERSION,
        "scope": SCOPE,
        "smoke_id": manifest.get("smoke_id"),
        "candidate_kind": manifest.get("candidate_kind"),
        "run_kind": run_kind,
        "eligible_for_api_smoke_denominator": not reasons,
        "benchmark_counting_enabled": False,
        "unit_headline_eligible": False,
        "not_eligible_reasons": reasons,
        "requirements": requirements,
    }


def _not_eligible_reasons(requirements: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if requirements.get("manifest_status_allowed") is not True:
        reasons.append("manifest_status_not_approved_or_active")
    if requirements.get("candidate_kind_matches") is not True:
        reasons.append("candidate_kind_mismatch")
    if requirements.get("target_matches_generation") is not True:
        reasons.append("target_mismatch")
    if requirements.get("api_evidence_present") is not True:
        reasons.append("api_evidence_absent")
    else:
        if requirements.get("api_evidence_candidate_kind_matches") is not True:
            reasons.append("api_evidence_candidate_kind_mismatch")
        if requirements.get("runner_tool_matches") is not True:
            reasons.append("runner_tool_mismatch")
        if requirements.get("redaction_contract_satisfied") is not True:
            reasons.append("redaction_contract_unsatisfied")
    if requirements.get("maven_judge_evidence_present") is not True:
        reasons.append("maven_judge_evidence_absent")
    if requirements.get("conclusion_needs_review") is not True:
        reasons.append("conclusion_not_need_human_review")
    if requirements.get("trusted_false") is not True:
        reasons.append("trusted_not_false")
    return reasons


def _optional_mapping(value: Any) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    return None
