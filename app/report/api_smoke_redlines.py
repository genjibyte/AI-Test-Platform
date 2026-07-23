"""Report-only API smoke red-line summary.

S8/S9/S10 already validate and project compact API smoke facts. This helper
adds a reviewer-facing boundary summary over those existing report fields. It
does not execute API calls, change digest/recommendation/conclusion/trusted,
write benchmark or ledger records, or grant authority.
"""
from __future__ import annotations

from typing import Any, Mapping

REDLINE_SUMMARY_VERSION = "api_smoke_redline_summary.v1"


def summarize_api_smoke_redlines(
    review_summary: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Summarize API smoke red-line facts already present in ``review_summary``.

    Returns ``None`` for ordinary unit-test reports. The summary is intentionally
    descriptive: it surfaces missing or unsafe-looking facts, but it never
    changes the review recommendation or final report authority.
    """
    api_evidence = _mapping_or_none(review_summary.get("api_evidence"))
    manifest = _mapping_or_none(review_summary.get("api_smoke_manifest"))
    denominator = _mapping_or_none(review_summary.get("api_smoke_denominator"))
    if not (api_evidence or manifest or denominator):
        return None
    alignment = _mapping_or_none((manifest or {}).get("alignment")) or {}
    api_evidence_supplied = _bool_or_none(alignment.get("api_evidence_present"))
    if api_evidence_supplied is None:
        api_evidence_supplied = api_evidence is not None
    effective_api_evidence = api_evidence if api_evidence_supplied else None

    redaction = _redaction_summary(effective_api_evidence, manifest)
    execution = _execution_boundary(effective_api_evidence, manifest)
    authority = _authority_boundary(effective_api_evidence, denominator)
    flags = _review_flags(
        api_evidence=effective_api_evidence,
        manifest=manifest,
        denominator=denominator,
        redaction=redaction,
        execution=execution,
        authority=authority,
    )

    return {
        "summary_version": REDLINE_SUMMARY_VERSION,
        "advisory": True,
        "report_only": True,
        "present": True,
        "candidate_kind": _candidate_kind(api_evidence, manifest, denominator),
        "smoke_id": _value_from("smoke_id", manifest, denominator),
        "api_evidence_present": api_evidence_supplied,
        "api_evidence_block_present": api_evidence is not None,
        "api_smoke_manifest_present": manifest is not None,
        "api_smoke_denominator_present": denominator is not None,
        "redaction": redaction,
        "execution_boundary": execution,
        "authority_boundary": authority,
        "review_flags": flags,
        "redlines_satisfied": not flags,
        "digest_signal": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "note": (
            "Reviewer-facing API smoke boundary summary only. It does not run "
            "an executor, change digest severity, alter benchmark/ledger "
            "analytics, or accept a candidate."
        ),
    }


def _redaction_summary(
    api_evidence: Mapping[str, Any] | None,
    manifest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    redaction = _mapping_or_none((api_evidence or {}).get("redaction")) or {}
    alignment = _mapping_or_none((manifest or {}).get("alignment")) or {}
    request_body = _bool_or_none(redaction.get("request_body_persisted"))
    response_body = _bool_or_none(redaction.get("response_body_persisted"))
    secrets = _bool_or_none(redaction.get("secrets_persisted"))
    if api_evidence is None:
        satisfied = None
    else:
        satisfied = request_body is False and response_body is False and secrets is False
    alignment_satisfied = _bool_or_none(
        alignment.get("redaction_contract_satisfied")
    )
    if alignment_satisfied is False:
        satisfied = False
    return {
        "request_body_persisted": request_body,
        "response_body_persisted": response_body,
        "secrets_persisted": secrets,
        "redaction_contract_satisfied": satisfied,
        "manifest_alignment_satisfied": alignment_satisfied,
    }


def _execution_boundary(
    api_evidence: Mapping[str, Any] | None,
    manifest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    evidence_execution = _mapping_or_none((api_evidence or {}).get("execution")) or {}
    manifest_policy = _mapping_or_none((manifest or {}).get("execution_policy")) or {}
    evidence_runner = _text_or_none(evidence_execution.get("runner_tool"))
    manifest_runner = _text_or_none(manifest_policy.get("runner_tool"))
    return {
        "evidence_runner_tool": evidence_runner,
        "manifest_runner_tool": manifest_runner,
        "runner_tool_matches": (
            None
            if evidence_runner is None or manifest_runner is None
            else evidence_runner == manifest_runner
        ),
        "external_network_allowed": _bool_or_none(
            manifest_policy.get("external_network_allowed")
        ),
        "docker_required": _bool_or_none(manifest_policy.get("docker_required")),
        "real_model_allowed": _bool_or_none(manifest_policy.get("real_model_allowed")),
        "external_execution_allowed_now": False,
    }


def _authority_boundary(
    api_evidence: Mapping[str, Any] | None,
    denominator: Mapping[str, Any] | None,
) -> dict[str, Any]:
    requirements = _mapping_or_none((denominator or {}).get("requirements")) or {}
    conclusion_needs_review = _bool_or_none(
        requirements.get("conclusion_needs_review")
    )
    trusted_false = _bool_or_none(requirements.get("trusted_false"))
    if conclusion_needs_review is None and api_evidence is not None:
        conclusion_needs_review = (
            api_evidence.get("conclusion") == "NEED_HUMAN_REVIEW"
        )
    if trusted_false is None and api_evidence is not None:
        trusted_false = api_evidence.get("trusted") is False

    return {
        "conclusion_needs_review": conclusion_needs_review,
        "trusted_false": trusted_false,
        "benchmark_counting_enabled": _bool_or_none(
            (denominator or {}).get("benchmark_counting_enabled")
        ),
        "unit_headline_eligible": _bool_or_none(
            (denominator or {}).get("unit_headline_eligible")
        ),
        "digest_signal": False,
        "verdict_authority": False,
        "trusted_authority": False,
    }


def _review_flags(
    *,
    api_evidence: Mapping[str, Any] | None,
    manifest: Mapping[str, Any] | None,
    denominator: Mapping[str, Any] | None,
    redaction: Mapping[str, Any],
    execution: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> list[str]:
    flags: list[str] = []
    if api_evidence is None:
        flags.append("api_evidence_absent")
    if manifest is None:
        flags.append("api_smoke_manifest_absent")
    if denominator is None and manifest is not None:
        flags.append("api_smoke_denominator_absent")

    _append_if_true(flags, redaction.get("request_body_persisted"), "request_body_persisted")
    _append_if_true(flags, redaction.get("response_body_persisted"), "response_body_persisted")
    _append_if_true(flags, redaction.get("secrets_persisted"), "secrets_persisted")
    if redaction.get("redaction_contract_satisfied") is False:
        flags.append("redaction_contract_unsatisfied")

    if execution.get("runner_tool_matches") is False:
        flags.append("runner_tool_mismatch")
    _append_if_true(
        flags,
        execution.get("external_network_allowed"),
        "external_network_allowed",
    )
    _append_if_true(flags, execution.get("docker_required"), "docker_required")
    _append_if_true(flags, execution.get("real_model_allowed"), "real_model_allowed")

    if authority.get("conclusion_needs_review") is False:
        flags.append("conclusion_not_need_human_review")
    if authority.get("trusted_false") is False:
        flags.append("trusted_not_false")
    _append_if_true(
        flags,
        authority.get("benchmark_counting_enabled"),
        "benchmark_counting_enabled",
    )
    _append_if_true(
        flags,
        authority.get("unit_headline_eligible"),
        "unit_headline_eligible",
    )

    if denominator is not None:
        for reason in _string_list(denominator.get("not_eligible_reasons")):
            if reason not in flags:
                flags.append(reason)
    return flags


def _candidate_kind(*sources: Mapping[str, Any] | None) -> str | None:
    return _value_from("candidate_kind", *sources)


def _value_from(key: str, *sources: Mapping[str, Any] | None) -> str | None:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _mapping_or_none(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _text_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _append_if_true(flags: list[str], value: Any, name: str) -> None:
    if value is True:
        flags.append(name)
