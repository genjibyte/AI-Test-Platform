"""Human review/RCA label validation (docs/57).

This module is intentionally pure and non-persistent. It normalizes labels that
were declared by a human or verifier, projects compact metric facts, and never
changes the platform verdict.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "human_review_label.v1"
METRIC_PROJECTION_VERSION = "human_review_metric_projection.v1"

DISPOSITIONS = ("kept", "kept_with_edits", "rejected", "deferred")
USABLE_DISPOSITIONS = {"kept", "kept_with_edits"}

MANUAL_REVISION_KINDS = (
    "assertion",
    "import",
    "mock",
    "fixture",
    "data",
    "target",
    "style",
    "other",
)

ROOT_CAUSE_CODES_BY_FAMILY = {
    "compile": {
        "compile_missing_symbol_or_import",
        "compile_api_signature_mismatch",
        "compile_type_or_generic_mismatch",
    },
    "execution": {
        "execution_test_runtime_error",
        "execution_no_tests_discovered",
    },
    "oracle": {
        "oracle_expected_behavior_wrong",
        "oracle_weak_or_missing",
        "oracle_spec_missing_or_ambiguous",
    },
    "mock": {"mock_misuse_or_overmocking"},
    "asset": {
        "asset_fixture_or_test_data_missing",
        "asset_schema_or_contract_missing",
        "asset_business_oracle_missing",
    },
    "environment": {
        "environment_policy_plugin_failure",
        "environment_coverage_or_instrumentation",
        "environment_service_or_dependency_unavailable",
    },
    "product": {
        "product_bug_confirmed",
        "product_bug_suspected",
    },
    "platform": {
        "platform_judge_bug",
        "platform_signal_misleading",
    },
    "unknown": {"unknown_insufficient_evidence"},
}
ROOT_CAUSE_FAMILIES = tuple(ROOT_CAUSE_CODES_BY_FAMILY.keys())
ROOT_CAUSE_CONFIDENCE = ("human_confirmed", "verifier_confirmed", "uncertain")

FIX_ACTIONS = (
    "add_import_or_symbol_reference",
    "adjust_api_call_or_overload",
    "fix_type_or_generic_use",
    "rewrite_assertion_or_expected_value",
    "add_behavior_or_business_oracle",
    "add_fixture_or_test_data",
    "replace_or_remove_mock",
    "stabilize_time_random_io",
    "configure_service_or_dependency",
    "mark_product_bug",
    "mark_not_actionable",
)

MISJUDGMENT_KINDS = (
    "none",
    "false_positive",
    "false_negative",
    "severity_mismatch",
    "unclear",
)
MISJUDGMENT_SIGNALS = (
    "quality_gate",
    "review_digest",
    "asset_gate",
    "router",
    "mutation",
    "other",
)

_FORBIDDEN_AUTHORITY_FIELDS = {
    "accepted",
    "auto_accept",
    "auto_accepted",
    "auto_merge",
    "auto_warehouse",
    "conclusion",
    "recommendation",
    "trusted",
}


class HumanLabelValidationError(ValueError):
    """Raised when a human review label violates the S5C contract."""


def validate_human_review_label(label: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a human review/RCA label.

    Missing review fields are allowed and mean "not reviewed yet". Fields that
    would grant platform authority, such as ``trusted`` or ``auto_accept``, are
    rejected because human labels are metric/reference facts, not acceptance
    commands.
    """
    if not isinstance(label, dict):
        raise HumanLabelValidationError("label must be a dict")

    _reject_forbidden_authority_fields(label)

    normalized = deepcopy(label)
    schema_version = normalized.setdefault("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise HumanLabelValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    disposition = normalized.get("disposition")
    if disposition is not None:
        _require_one_of("disposition", disposition, DISPOSITIONS)

    count = _normalize_manual_revision_count(normalized)
    kinds = _normalize_manual_revision_kinds(normalized)

    if disposition == "kept_with_edits":
        if count <= 0:
            raise HumanLabelValidationError(
                "kept_with_edits requires manual_revision_count > 0"
            )
        if not kinds:
            raise HumanLabelValidationError(
                "kept_with_edits requires at least one manual_revision_kinds entry"
            )
    if count > 0 and not kinds:
        raise HumanLabelValidationError(
            "manual_revision_count > 0 requires manual_revision_kinds"
        )
    if disposition == "rejected" and not (
        normalized.get("disposition_reason") or normalized.get("root_cause")
    ):
        raise HumanLabelValidationError(
            "rejected labels require disposition_reason or root_cause"
        )
    if disposition == "deferred" and not (
        normalized.get("disposition_reason") or normalized.get("root_cause")
    ):
        raise HumanLabelValidationError(
            "deferred labels require disposition_reason or root_cause"
        )

    _validate_optional_timestamp(normalized, "review_started_at")
    _validate_optional_timestamp(normalized, "review_completed_at")
    _validate_review_time_order(normalized)

    if normalized.get("root_cause") is not None:
        _validate_root_cause(normalized["root_cause"])
    if normalized.get("fix_note") is not None:
        _validate_fix_note(normalized["fix_note"])
    if normalized.get("misjudgment") is not None:
        _validate_misjudgment(normalized["misjudgment"])

    return normalized


def label_metric_projection(label: dict[str, Any]) -> dict[str, Any]:
    """Project a validated label into compact metric facts.

    The projection is deliberately small: it makes human/golden metrics easier
    to compute later, but it does not persist anything or convert a human label
    into a verdict.
    """
    normalized = validate_human_review_label(label)

    disposition = normalized.get("disposition")
    root = normalized.get("root_cause") or {}
    fix = normalized.get("fix_note") or {}
    misjudgment = normalized.get("misjudgment") or {}

    return {
        "schema_version": METRIC_PROJECTION_VERSION,
        "source_schema_version": normalized["schema_version"],
        "human_reviewed": disposition is not None,
        "disposition": disposition,
        "usable_test": (
            disposition in USABLE_DISPOSITIONS if disposition is not None else None
        ),
        "manual_revision_count": normalized.get("manual_revision_count", 0),
        "manual_revision_kinds": list(normalized.get("manual_revision_kinds") or []),
        "human_handling_time_seconds": _duration_seconds(
            normalized.get("review_started_at"),
            normalized.get("review_completed_at"),
        ),
        "root_cause_family": root.get("family"),
        "root_cause_code": root.get("code"),
        "root_cause_confidence": root.get("confidence"),
        "root_cause_recorded": bool(root.get("recorded_at")),
        "defect_discovery_label": root.get("code") == "product_bug_confirmed",
        "fix_action": fix.get("action"),
        "changed_test": fix.get("changed_test"),
        "changed_production": fix.get("changed_production"),
        "misjudgment_kind": misjudgment.get("kind"),
        "misjudgment_signal": misjudgment.get("platform_signal"),
        "misled_human": misjudgment.get("misled_human"),
        "advisory_only": True,
        "conclusion": "NEED_HUMAN_REVIEW",
        "trusted": False,
    }


def _reject_forbidden_authority_fields(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in _FORBIDDEN_AUTHORITY_FIELDS:
                raise HumanLabelValidationError(
                    f"human label must not contain authority field: {child_path}"
                )
            _reject_forbidden_authority_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_authority_fields(child, f"{path}[{index}]")


def _normalize_manual_revision_count(label: dict[str, Any]) -> int:
    count = label.get("manual_revision_count", 0)
    if isinstance(count, bool) or not isinstance(count, int):
        raise HumanLabelValidationError("manual_revision_count must be an integer")
    if count < 0:
        raise HumanLabelValidationError("manual_revision_count must be >= 0")
    label["manual_revision_count"] = count
    return count


def _normalize_manual_revision_kinds(label: dict[str, Any]) -> list[str]:
    kinds = label.get("manual_revision_kinds") or []
    if not isinstance(kinds, list):
        raise HumanLabelValidationError("manual_revision_kinds must be a list")
    for kind in kinds:
        _require_one_of("manual_revision_kind", kind, MANUAL_REVISION_KINDS)
    label["manual_revision_kinds"] = list(kinds)
    return label["manual_revision_kinds"]


def _validate_root_cause(root: dict[str, Any]) -> None:
    if not isinstance(root, dict):
        raise HumanLabelValidationError("root_cause must be a dict")

    family = root.get("family")
    code = root.get("code")
    confidence = root.get("confidence")
    if family is None or code is None or confidence is None:
        raise HumanLabelValidationError(
            "root_cause requires family, code, and confidence"
        )
    _require_one_of("root_cause.family", family, ROOT_CAUSE_FAMILIES)
    _require_one_of("root_cause.confidence", confidence, ROOT_CAUSE_CONFIDENCE)
    _require_one_of("root_cause.code", code, ROOT_CAUSE_CODES_BY_FAMILY[family])

    evidence_refs = root.get("evidence_refs") or []
    if not isinstance(evidence_refs, list):
        raise HumanLabelValidationError("root_cause.evidence_refs must be a list")
    if any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs):
        raise HumanLabelValidationError(
            "root_cause.evidence_refs must contain non-empty strings"
        )

    if code == "product_bug_confirmed":
        if confidence not in {"human_confirmed", "verifier_confirmed"}:
            raise HumanLabelValidationError(
                "product_bug_confirmed requires human/verifier confirmation"
            )
        if not evidence_refs:
            raise HumanLabelValidationError(
                "product_bug_confirmed requires evidence_refs"
            )

    _validate_optional_timestamp(root, "recorded_at", prefix="root_cause")


def _validate_fix_note(fix_note: dict[str, Any]) -> None:
    if not isinstance(fix_note, dict):
        raise HumanLabelValidationError("fix_note must be a dict")

    action = fix_note.get("action")
    if action is None:
        raise HumanLabelValidationError("fix_note requires action")
    _require_one_of("fix_note.action", action, FIX_ACTIONS)

    for key in ("changed_test", "changed_production"):
        value = fix_note.get(key)
        if value is not None and not isinstance(value, bool):
            raise HumanLabelValidationError(f"fix_note.{key} must be boolean")


def _validate_misjudgment(misjudgment: dict[str, Any]) -> None:
    if not isinstance(misjudgment, dict):
        raise HumanLabelValidationError("misjudgment must be a dict")

    kind = misjudgment.get("kind", "none")
    _require_one_of("misjudgment.kind", kind, MISJUDGMENT_KINDS)

    platform_signal = misjudgment.get("platform_signal")
    if platform_signal is not None:
        _require_one_of(
            "misjudgment.platform_signal",
            platform_signal,
            MISJUDGMENT_SIGNALS,
        )

    if kind != "none":
        if platform_signal is None:
            raise HumanLabelValidationError(
                "non-none misjudgment requires platform_signal"
            )
        if not misjudgment.get("human_verdict"):
            raise HumanLabelValidationError(
                "non-none misjudgment requires human_verdict"
            )

    misled = misjudgment.get("misled_human")
    if misled is not None and not isinstance(misled, bool):
        raise HumanLabelValidationError("misjudgment.misled_human must be boolean or null")


def _require_one_of(name: str, value: Any, allowed: tuple[str, ...] | set[str]) -> None:
    if value not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise HumanLabelValidationError(f"{name} must be one of: {allowed_text}")


def _validate_optional_timestamp(
    value: dict[str, Any],
    key: str,
    *,
    prefix: str | None = None,
) -> None:
    timestamp = value.get(key)
    if timestamp is None:
        return
    if not isinstance(timestamp, str):
        name = f"{prefix}.{key}" if prefix else key
        raise HumanLabelValidationError(f"{name} must be an ISO-8601 string")
    _parse_iso8601(timestamp, f"{prefix}.{key}" if prefix else key)


def _validate_review_time_order(label: dict[str, Any]) -> None:
    started = label.get("review_started_at")
    completed = label.get("review_completed_at")
    if not started or not completed:
        return
    if _parse_iso8601(completed, "review_completed_at") < _parse_iso8601(
        started,
        "review_started_at",
    ):
        raise HumanLabelValidationError(
            "review_completed_at must be after review_started_at"
        )


def _duration_seconds(started: str | None, completed: str | None) -> int | None:
    if not started or not completed:
        return None
    delta = _parse_iso8601(completed, "review_completed_at") - _parse_iso8601(
        started,
        "review_started_at",
    )
    return int(delta.total_seconds())


def _parse_iso8601(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HumanLabelValidationError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
