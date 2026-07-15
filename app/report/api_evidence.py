"""Compact API/interface evidence block validation (docs/60_api_candidate/04).

The block is a future ``review_summary["api_evidence"]`` shape. This module is
pure: it does not execute candidates, discover services, alter reports, or grant
trust. It only normalizes compact fact fields and rejects payload/secret drift.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "api_evidence.v1"

JUNIT_API_CANDIDATE = "junit_api_candidate"
API_SCHEMA_CANDIDATE = "api_schema_candidate"
API_COLLECTION_CANDIDATE = "api_collection_candidate"
INTEGRATION_FLOW_CANDIDATE = "integration_flow_candidate"
ALLOWED_CANDIDATE_KINDS = (
    JUNIT_API_CANDIDATE,
    API_SCHEMA_CANDIDATE,
    API_COLLECTION_CANDIDATE,
    INTEGRATION_FLOW_CANDIDATE,
)

REQUIREMENT_STATUSES = ("not_required", "present", "missing", "failed", "unknown")
SERVICE_START_STATUSES = ("not_required", "skipped", "passed", "failed", "unknown")
NETWORK_SCOPES = ("local", "sandbox", "external", "unknown")
RUNNER_TOOLS = ("maven_surefire_jacoco", "schemathesis", "newman", "unknown")
STATUS_CLASSES = ("2xx", "3xx", "4xx", "5xx", "other")
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "OTHER")
FAILURE_SEVERITIES = ("blocker", "warning")
FAILURE_CODES = (
    "api_asset_missing_schema",
    "api_asset_missing_collection",
    "api_asset_missing_base_url",
    "api_auth_unconfigured",
    "api_fixture_missing",
    "api_fixture_setup_failure",
    "api_mock_missing",
    "api_service_start_failure",
    "api_no_requests_executed",
    "api_schema_violation",
    "api_assertion_failure",
    "api_unexpected_status",
    "api_http_5xx",
    "api_runner_timeout",
    "api_runner_error",
    "api_environment_scope_violation",
    "api_redaction_required",
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
_FORBIDDEN_PAYLOAD_OR_SECRET_KEYS = {
    ".env",
    "authorization",
    "cookie",
    "cookies",
    "password",
    "payload",
    "raw_payload",
    "raw_request",
    "raw_response",
    "request_body",
    "request_body_raw",
    "response_body",
    "response_body_raw",
    "secret",
    "secrets",
    "token",
}


class ApiEvidenceValidationError(ValueError):
    """Raised when an API evidence block violates the compact S6C contract."""


def empty_api_evidence(
    *,
    candidate_kind: str = JUNIT_API_CANDIDATE,
) -> dict[str, Any]:
    """Return the minimal empty report-only API evidence block."""
    return validate_api_evidence_block({"candidate_kind": candidate_kind})


def validate_api_evidence_block(block: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a compact API/interface evidence block.

    The function accepts sparse input and fills safe defaults. It rejects
    authority fields and raw payload/secret-like keys anywhere in the block.
    """
    if not isinstance(block, Mapping):
        raise ApiEvidenceValidationError("api_evidence block must be a mapping")

    _reject_forbidden_fields(block)
    data = deepcopy(dict(block))

    schema_version = data.setdefault("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise ApiEvidenceValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    candidate_kind = data.get("candidate_kind", JUNIT_API_CANDIDATE)
    _require_one_of("candidate_kind", candidate_kind, ALLOWED_CANDIDATE_KINDS)

    normalized = {
        "schema_version": schema_version,
        "advisory": _normalize_required_bool(data.get("advisory", True), "advisory"),
        "report_only": _normalize_required_bool(
            data.get("report_only", True),
            "report_only",
        ),
        "candidate_kind": candidate_kind,
        "asset_refs": _normalize_asset_refs(data.get("asset_refs")),
        "environment": _normalize_environment(data.get("environment")),
        "execution": _normalize_execution(data.get("execution")),
        "traffic": _normalize_traffic(data.get("traffic")),
        "checks": _normalize_checks(data.get("checks")),
        "failures": _normalize_failures(data.get("failures")),
        "redaction": _normalize_redaction(data.get("redaction")),
        "conclusion": "NEED_HUMAN_REVIEW",
        "trusted": False,
    }

    if normalized["advisory"] is not True:
        raise ApiEvidenceValidationError("api_evidence must be advisory=true")
    if normalized["report_only"] is not True:
        raise ApiEvidenceValidationError("api_evidence must be report_only=true")

    return normalized


def _normalize_asset_refs(value: Any) -> dict[str, Any]:
    asset_refs = _mapping(value)
    return {
        "schema_ref_present": _optional_bool(
            asset_refs.get("schema_ref_present"),
            "asset_refs.schema_ref_present",
        ),
        "collection_ref_present": _optional_bool(
            asset_refs.get("collection_ref_present"),
            "asset_refs.collection_ref_present",
        ),
        "base_url_ref_present": _optional_bool(
            asset_refs.get("base_url_ref_present"),
            "asset_refs.base_url_ref_present",
        ),
        "auth_requirement": _status(
            asset_refs.get("auth_requirement", "unknown"),
            "asset_refs.auth_requirement",
            REQUIREMENT_STATUSES,
        ),
        "fixture_requirement": _status(
            asset_refs.get("fixture_requirement", "unknown"),
            "asset_refs.fixture_requirement",
            REQUIREMENT_STATUSES,
        ),
        "mock_requirement": _status(
            asset_refs.get("mock_requirement", "unknown"),
            "asset_refs.mock_requirement",
            REQUIREMENT_STATUSES,
        ),
    }


def _normalize_environment(value: Any) -> dict[str, Any]:
    environment = _mapping(value)
    return {
        "service_start": _status(
            environment.get("service_start", "unknown"),
            "environment.service_start",
            SERVICE_START_STATUSES,
        ),
        "base_url_available": _optional_bool(
            environment.get("base_url_available"),
            "environment.base_url_available",
        ),
        "network_scope": _status(
            environment.get("network_scope", "unknown"),
            "environment.network_scope",
            NETWORK_SCOPES,
        ),
    }


def _normalize_execution(value: Any) -> dict[str, Any]:
    execution = _mapping(value)
    return {
        "runner_tool": _status(
            execution.get("runner_tool", "unknown"),
            "execution.runner_tool",
            RUNNER_TOOLS,
        ),
        "command_summary": _optional_str(
            execution.get("command_summary"),
            "execution.command_summary",
        ),
        "duration_ms": _optional_non_negative_int(
            execution.get("duration_ms"),
            "execution.duration_ms",
        ),
        "log_path": _optional_str(execution.get("log_path"), "execution.log_path"),
    }


def _normalize_traffic(value: Any) -> dict[str, Any]:
    traffic = _mapping(value)
    return {
        "request_count": _non_negative_int(
            traffic.get("request_count", 0),
            "traffic.request_count",
        ),
        "operation_count": _non_negative_int(
            traffic.get("operation_count", 0),
            "traffic.operation_count",
        ),
        "status_summary": _normalize_status_summary(
            traffic.get("status_summary") or []
        ),
        "method_path_summary": _normalize_method_path_summary(
            traffic.get("method_path_summary") or []
        ),
    }


def _normalize_checks(value: Any) -> dict[str, int]:
    checks = _mapping(value)
    names = (
        "schema_failures",
        "assertion_failures",
        "auth_failures",
        "fixture_failures",
        "mock_misses",
        "service_start_failures",
        "runner_errors",
        "timeouts",
    )
    return {
        name: _non_negative_int(checks.get(name, 0), f"checks.{name}")
        for name in names
    }


def _normalize_failures(value: Any) -> list[dict[str, str]]:
    failures = value or []
    if not isinstance(failures, list):
        raise ApiEvidenceValidationError("failures must be a list")

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(failures):
        failure = _mapping(item, f"failures[{index}]")
        code = failure.get("code")
        severity = failure.get("severity")
        evidence = failure.get("evidence")
        _require_one_of(f"failures[{index}].code", code, FAILURE_CODES)
        _require_one_of(f"failures[{index}].severity", severity, FAILURE_SEVERITIES)
        if not isinstance(evidence, str) or not evidence.strip():
            raise ApiEvidenceValidationError(
                f"failures[{index}].evidence must be a non-empty redacted string"
            )
        normalized.append({
            "code": code,
            "severity": severity,
            "evidence": evidence.strip(),
        })
    return normalized


def _normalize_redaction(value: Any) -> dict[str, bool]:
    redaction = _mapping(value)
    normalized = {
        "request_body_persisted": _normalize_required_bool(
            redaction.get("request_body_persisted", False),
            "redaction.request_body_persisted",
        ),
        "response_body_persisted": _normalize_required_bool(
            redaction.get("response_body_persisted", False),
            "redaction.response_body_persisted",
        ),
        "secrets_persisted": _normalize_required_bool(
            redaction.get("secrets_persisted", False),
            "redaction.secrets_persisted",
        ),
    }
    if any(normalized.values()):
        raise ApiEvidenceValidationError(
            "api_evidence must not persist request bodies, response bodies, or secrets"
        )
    return normalized


def _normalize_status_summary(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ApiEvidenceValidationError("traffic.status_summary must be a list")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        row = _mapping(item, f"traffic.status_summary[{index}]")
        cls = row.get("class")
        _require_one_of(
            f"traffic.status_summary[{index}].class",
            cls,
            STATUS_CLASSES,
        )
        normalized.append({
            "class": cls,
            "count": _non_negative_int(
                row.get("count", 0),
                f"traffic.status_summary[{index}].count",
            ),
        })
    return normalized


def _normalize_method_path_summary(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ApiEvidenceValidationError("traffic.method_path_summary must be a list")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        row = _mapping(item, f"traffic.method_path_summary[{index}]")
        method = row.get("method")
        if isinstance(method, str):
            method = method.upper()
        _require_one_of(
            f"traffic.method_path_summary[{index}].method",
            method,
            HTTP_METHODS,
        )
        path_template = row.get("path_template")
        if not isinstance(path_template, str) or not path_template.startswith("/"):
            raise ApiEvidenceValidationError(
                f"traffic.method_path_summary[{index}].path_template must start with /"
            )
        normalized.append({
            "method": method,
            "path_template": path_template,
            "count": _non_negative_int(
                row.get("count", 0),
                f"traffic.method_path_summary[{index}].count",
            ),
        })
    return normalized


def _reject_forbidden_fields(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            lowered = key_text.lower()
            if lowered in _FORBIDDEN_AUTHORITY_FIELDS:
                raise ApiEvidenceValidationError(
                    f"api_evidence must not contain authority field: {child_path}"
                )
            if lowered in _FORBIDDEN_PAYLOAD_OR_SECRET_KEYS:
                raise ApiEvidenceValidationError(
                    f"api_evidence must not persist raw payload/secret field: {child_path}"
                )
            _reject_forbidden_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


def _mapping(value: Any, name: str = "value") -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ApiEvidenceValidationError(f"{name} must be a mapping")
    return value


def _status(name: Any, field: str, allowed: tuple[str, ...]) -> str:
    _require_one_of(field, name, allowed)
    return str(name)


def _require_one_of(name: str, value: Any, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        allowed_text = ", ".join(allowed)
        raise ApiEvidenceValidationError(f"{name} must be one of: {allowed_text}")


def _optional_bool(value: Any, name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise ApiEvidenceValidationError(f"{name} must be true, false, or null")


def _normalize_required_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ApiEvidenceValidationError(f"{name} must be boolean")


def _non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiEvidenceValidationError(f"{name} must be an integer")
    if value < 0:
        raise ApiEvidenceValidationError(f"{name} must be >= 0")
    return value


def _optional_non_negative_int(value: Any, name: str) -> int | None:
    if value is None:
        return None
    return _non_negative_int(value, name)


def _optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiEvidenceValidationError(f"{name} must be a string")
    return value
