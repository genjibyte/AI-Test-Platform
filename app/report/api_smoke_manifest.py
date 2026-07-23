"""JUnit API smoke manifest validation (docs/60_api_candidate/07).

The manifest is a future proof denominator for ``junit_api_candidate`` smoke
rows. This module is pure: it does not execute candidates, start services,
wire submit/report paths, alter benchmark/ledger schemas, or grant trust.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "api_smoke_manifest.v1"

JUNIT_API_CANDIDATE = "junit_api_candidate"
RUNNER_TOOL = "maven_surefire_jacoco"
REPORT_PATH = "review_summary.api_evidence"
DEFAULT_TIMEOUT_POLICY_REF = "current judge timeout"

MANIFEST_STATUSES = ("designed", "approved", "active", "retired")
API_STYLES = ("mockmvc", "webtestclient", "restassured_local", "local_http", "unknown")
SUT_INTAKE_SHAPES = ("none", "sut_target")
REQUIREMENT_LEVELS = ("not_required", "required", "unknown")
BUSINESS_ORACLE_REQUIREMENTS = ("present", "missing", "unknown")
NETWORK_SCOPES = ("local", "sandbox")

CANONICAL_REQUIRED_FIELDS = (
    "target_class",
    "test_source",
    "producer_id",
    "candidate_kind",
)
CANONICAL_OPTIONAL_FIELDS = ("target_method", "producer_meta", "api_evidence")
CANONICAL_FORBIDDEN = (
    "raw request bodies",
    "raw response bodies",
    "tokens",
    "cookies",
    "credentials",
    ".env values",
    "database dumps",
    "service snapshots",
    "conclusion",
    "trusted",
    "auto_accept",
)
MINIMUM_API_EVIDENCE = {
    "advisory": True,
    "report_only": True,
    "candidate_kind": JUNIT_API_CANDIDATE,
    "execution.runner_tool": RUNNER_TOOL,
    "redaction.request_body_persisted": False,
    "redaction.response_body_persisted": False,
    "redaction.secrets_persisted": False,
}

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
    "credential",
    "credentials",
    "database_dump",
    "database_dumps",
    "password",
    "payload",
    "raw_payload",
    "raw_request",
    "raw_response",
    "raw_traffic",
    "request_body",
    "request_body_raw",
    "response_body",
    "response_body_raw",
    "secret",
    "secrets",
    "service_snapshot",
    "service_snapshots",
    "token",
    "tokens",
}


class ApiSmokeManifestValidationError(ValueError):
    """Raised when an API smoke manifest violates the S7C contract."""


def validate_api_smoke_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a compact ``api_smoke_manifest.v1`` row.

    Sparse input is allowed where the S7C design supplies safe defaults. The
    validator rejects authority fields, raw payload/secret-like keys, external
    execution drift, unsupported candidate kinds, and unaudited external SUTs.
    """
    if not isinstance(manifest, Mapping):
        raise ApiSmokeManifestValidationError("api_smoke_manifest must be a mapping")

    _reject_forbidden_fields(manifest)
    data = deepcopy(dict(manifest))

    schema_version = data.setdefault("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise ApiSmokeManifestValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    smoke_id = _required_non_empty_str(data.get("smoke_id"), "smoke_id")
    candidate_kind = data.get("candidate_kind", JUNIT_API_CANDIDATE)
    if candidate_kind != JUNIT_API_CANDIDATE:
        raise ApiSmokeManifestValidationError(
            "api_smoke_manifest supports only junit_api_candidate in S7C"
        )

    return {
        "schema_version": schema_version,
        "smoke_id": smoke_id,
        "candidate_kind": JUNIT_API_CANDIDATE,
        "status": _status(data.get("status", "designed"), "status", MANIFEST_STATUSES),
        "target": _normalize_target(data.get("target")),
        "submission_contract": _normalize_submission_contract(
            data.get("submission_contract")
        ),
        "asset_requirements": _normalize_asset_requirements(
            data.get("asset_requirements")
        ),
        "execution_policy": _normalize_execution_policy(data.get("execution_policy")),
        "evidence_contract": _normalize_evidence_contract(data.get("evidence_contract")),
    }


def _normalize_target(value: Any) -> dict[str, Any]:
    target = _mapping(value, "target")
    return {
        "target_class": _required_non_empty_str(
            target.get("target_class"),
            "target.target_class",
        ),
        "target_method": _optional_str(target.get("target_method"), "target.target_method"),
        "api_style": _status(
            target.get("api_style", "unknown"),
            "target.api_style",
            API_STYLES,
        ),
        "sut_ref": _normalize_sut_ref(target.get("sut_ref")),
    }


def _normalize_sut_ref(value: Any) -> dict[str, Any]:
    sut_ref = _mapping(value, "target.sut_ref")
    intake_shape = _status(
        sut_ref.get("intake_shape", "none"),
        "target.sut_ref.intake_shape",
        SUT_INTAKE_SHAPES,
    )
    normalized = {
        "intake_shape": intake_shape,
        "name": _optional_str(
            sut_ref.get("name", "project-under-judge"),
            "target.sut_ref.name",
        ),
        "url": _optional_str(sut_ref.get("url"), "target.sut_ref.url"),
        "commit": _optional_str(sut_ref.get("commit"), "target.sut_ref.commit"),
        "readme_audit_ref": _optional_str(
            sut_ref.get("readme_audit_ref"),
            "target.sut_ref.readme_audit_ref",
        ),
        "license_note": _optional_str(
            sut_ref.get("license_note"),
            "target.sut_ref.license_note",
        ),
    }
    if intake_shape == "sut_target":
        if not normalized["name"]:
            raise ApiSmokeManifestValidationError(
                "target.sut_ref.name is required for sut_target"
            )
        if not normalized["readme_audit_ref"]:
            raise ApiSmokeManifestValidationError(
                "target.sut_ref.readme_audit_ref is required for sut_target"
            )
    return normalized


def _normalize_submission_contract(value: Any) -> dict[str, Any]:
    contract = _mapping(value, "submission_contract")
    required_fields = _normalize_string_list(
        contract.get("required_fields", list(CANONICAL_REQUIRED_FIELDS)),
        "submission_contract.required_fields",
    )
    optional_fields = _normalize_string_list(
        contract.get("optional_fields", list(CANONICAL_OPTIONAL_FIELDS)),
        "submission_contract.optional_fields",
    )
    for field in CANONICAL_REQUIRED_FIELDS:
        if field not in required_fields:
            raise ApiSmokeManifestValidationError(
                f"submission_contract.required_fields must include {field}"
            )

    fixed_values = _mapping(contract.get("fixed_values"), "submission_contract.fixed_values")
    fixed_candidate_kind = fixed_values.get("candidate_kind", JUNIT_API_CANDIDATE)
    if fixed_candidate_kind != JUNIT_API_CANDIDATE:
        raise ApiSmokeManifestValidationError(
            "submission_contract.fixed_values.candidate_kind must be junit_api_candidate"
        )

    return {
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "fixed_values": {"candidate_kind": JUNIT_API_CANDIDATE},
    }


def _normalize_asset_requirements(value: Any) -> dict[str, str]:
    requirements = _mapping(value, "asset_requirements")
    return {
        "service_start_requirement": _status(
            requirements.get("service_start_requirement", "unknown"),
            "asset_requirements.service_start_requirement",
            REQUIREMENT_LEVELS,
        ),
        "base_url_requirement": _status(
            requirements.get("base_url_requirement", "unknown"),
            "asset_requirements.base_url_requirement",
            REQUIREMENT_LEVELS,
        ),
        "auth_requirement": _status(
            requirements.get("auth_requirement", "unknown"),
            "asset_requirements.auth_requirement",
            REQUIREMENT_LEVELS,
        ),
        "fixture_requirement": _status(
            requirements.get("fixture_requirement", "unknown"),
            "asset_requirements.fixture_requirement",
            REQUIREMENT_LEVELS,
        ),
        "mock_requirement": _status(
            requirements.get("mock_requirement", "unknown"),
            "asset_requirements.mock_requirement",
            REQUIREMENT_LEVELS,
        ),
        "business_oracle_ref_requirement": _status(
            requirements.get("business_oracle_ref_requirement", "unknown"),
            "asset_requirements.business_oracle_ref_requirement",
            BUSINESS_ORACLE_REQUIREMENTS,
        ),
    }


def _normalize_execution_policy(value: Any) -> dict[str, Any]:
    policy = _mapping(value, "execution_policy")
    runner_tool = policy.get("runner_tool", RUNNER_TOOL)
    if runner_tool != RUNNER_TOOL:
        raise ApiSmokeManifestValidationError(
            "execution_policy.runner_tool must be maven_surefire_jacoco"
        )

    normalized = {
        "runner_tool": RUNNER_TOOL,
        "allowed_network_scope": _status(
            policy.get("allowed_network_scope", "local"),
            "execution_policy.allowed_network_scope",
            NETWORK_SCOPES,
        ),
        "external_network_allowed": _required_bool(
            policy.get("external_network_allowed", False),
            "execution_policy.external_network_allowed",
        ),
        "docker_required": _required_bool(
            policy.get("docker_required", False),
            "execution_policy.docker_required",
        ),
        "real_model_allowed": _required_bool(
            policy.get("real_model_allowed", False),
            "execution_policy.real_model_allowed",
        ),
        "timeout_policy_ref": _optional_str(
            policy.get("timeout_policy_ref", DEFAULT_TIMEOUT_POLICY_REF),
            "execution_policy.timeout_policy_ref",
        ),
    }
    if normalized["external_network_allowed"] is not False:
        raise ApiSmokeManifestValidationError(
            "execution_policy.external_network_allowed must be false"
        )
    if normalized["docker_required"] is not False:
        raise ApiSmokeManifestValidationError(
            "execution_policy.docker_required must be false"
        )
    if normalized["real_model_allowed"] is not False:
        raise ApiSmokeManifestValidationError(
            "execution_policy.real_model_allowed must be false"
        )
    return normalized


def _normalize_evidence_contract(value: Any) -> dict[str, Any]:
    contract = _mapping(value, "evidence_contract")
    report_path = contract.get("report_path", REPORT_PATH)
    if report_path != REPORT_PATH:
        raise ApiSmokeManifestValidationError(
            "evidence_contract.report_path must be review_summary.api_evidence"
        )

    minimum_api_evidence = _mapping(
        contract.get("minimum_api_evidence"),
        "evidence_contract.minimum_api_evidence",
    )
    for key, expected in MINIMUM_API_EVIDENCE.items():
        actual = minimum_api_evidence.get(key, expected)
        if actual != expected:
            raise ApiSmokeManifestValidationError(
                f"evidence_contract.minimum_api_evidence.{key} must be {expected!r}"
            )

    forbidden = _normalize_string_list(
        contract.get("forbidden", list(CANONICAL_FORBIDDEN)),
        "evidence_contract.forbidden",
    )
    for item in CANONICAL_FORBIDDEN:
        if item not in forbidden:
            raise ApiSmokeManifestValidationError(
                f"evidence_contract.forbidden must include {item}"
            )

    return {
        "report_path": REPORT_PATH,
        "minimum_api_evidence": dict(MINIMUM_API_EVIDENCE),
        "forbidden": forbidden,
    }


def _reject_forbidden_fields(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            lowered = key_text.lower()
            if lowered in _FORBIDDEN_AUTHORITY_FIELDS:
                raise ApiSmokeManifestValidationError(
                    f"api_smoke_manifest must not contain authority field: {child_path}"
                )
            if lowered in _FORBIDDEN_PAYLOAD_OR_SECRET_KEYS:
                raise ApiSmokeManifestValidationError(
                    "api_smoke_manifest must not persist raw payload/secret field: "
                    f"{child_path}"
                )
            _reject_forbidden_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


def _mapping(value: Any, name: str = "value") -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ApiSmokeManifestValidationError(f"{name} must be a mapping")
    return value


def _normalize_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ApiSmokeManifestValidationError(f"{name} must be a list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ApiSmokeManifestValidationError(
                f"{name}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    return normalized


def _status(value: Any, field: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        allowed_text = ", ".join(allowed)
        raise ApiSmokeManifestValidationError(
            f"{field} must be one of: {allowed_text}"
        )
    return str(value)


def _required_non_empty_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApiSmokeManifestValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiSmokeManifestValidationError(f"{name} must be a string")
    stripped = value.strip()
    return stripped or None


def _required_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ApiSmokeManifestValidationError(f"{name} must be boolean")
