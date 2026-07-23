"""External README audit record validation.

README audits are design-time fact records. They do not authorize cloning into
the project tree, installing dependencies, executing tools, connecting to
external databases, downloading datasets, or changing verdicts.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from app.governance.external_assets import validate_external_asset_record

EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION = "external_repo_readme_audit.v1"

_AUDIT_FITS = {
    "knowledge_only",
    "metadata_seed_candidate",
    "future_adapter_candidate",
    "sut_reference_candidate",
    "defer",
    "reject_mainline",
}

_REQUIRED_AUDIT_FIELDS = (
    "audit_id",
    "audited_at",
    "auditor",
    "asset_record",
    "source_refs",
    "observed",
    "project_fit",
    "authority",
)

_OPTIONAL_AUDIT_FIELDS = (
    "schema_version",
    "notes",
)

_REQUIRED_OBSERVED_FIELDS = (
    "license",
    "runtime",
    "input_format",
    "output_or_evidence",
    "can_run_offline",
    "requires_network",
    "requires_docker",
    "requires_model_or_api_key",
    "writes_workspace",
    "secrets_or_payload_risk",
)

_REQUIRED_PROJECT_FIT_FIELDS = (
    "fit",
    "affects_artifact",
    "expected_evidence",
    "risks",
    "next_action",
)

_AUTHORITY_FIELDS = (
    "runtime_allowed",
    "download_allowed",
    "install_allowed",
    "vendor_code_allowed",
    "verdict_authority",
)

_FORBIDDEN_AUDIT_KEYS = {
    ".env",
    "accepted",
    "api_key",
    "authorization",
    "auto_accept",
    "auto_merge",
    "auto_warehouse",
    "cookie",
    "credentials",
    "database_dump",
    "password",
    "payload",
    "raw_payload",
    "raw_request",
    "raw_response",
    "request_body",
    "response_body",
    "secret",
    "secrets",
    "service_snapshot",
    "token",
    "trusted",
}

_SECRET_URL_MARKERS = (
    "api_key=",
    "apikey=",
    "access_token=",
    "auth=",
    "authorization=",
    "password=",
    "secret=",
    "token=",
)


class ExternalRepoReadmeAuditValidationError(ValueError):
    """Raised when a README audit record violates the governance contract."""


def validate_external_repo_readme_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one external repo README audit record."""
    if not isinstance(audit, Mapping):
        raise ExternalRepoReadmeAuditValidationError(
            "external repo README audit must be a mapping"
        )

    _reject_forbidden_audit_fields(audit)
    _reject_unknown_audit_fields(audit)

    missing = [field for field in _REQUIRED_AUDIT_FIELDS if field not in audit]
    if missing:
        raise ExternalRepoReadmeAuditValidationError(
            "external repo README audit missing required fields: " + ", ".join(missing)
        )

    schema_version = _optional_str(
        audit.get("schema_version", EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION),
        "schema_version",
    )
    if schema_version != EXTERNAL_REPO_README_AUDIT_SCHEMA_VERSION:
        raise ExternalRepoReadmeAuditValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    try:
        asset_record = validate_external_asset_record(audit["asset_record"])
    except ValueError as exc:
        raise ExternalRepoReadmeAuditValidationError(
            f"asset_record invalid: {exc}"
        ) from exc

    source_refs = _string_list(audit["source_refs"], "source_refs")
    for index, source_ref in enumerate(source_refs):
        if _url_looks_secret_bearing(source_ref):
            raise ExternalRepoReadmeAuditValidationError(
                f"source_refs[{index}] must not contain secret-like query parameters"
            )

    observed = _normalize_observed(audit["observed"])
    project_fit = _normalize_project_fit(audit["project_fit"])
    authority = _normalize_authority(audit["authority"])

    return {
        "schema_version": schema_version,
        "audit_id": _required_str(audit["audit_id"], "audit_id"),
        "audited_at": _iso_date(audit["audited_at"], "audited_at"),
        "auditor": _required_str(audit["auditor"], "auditor"),
        "asset_record": asset_record,
        "source_refs": source_refs,
        "observed": observed,
        "project_fit": project_fit,
        "authority": authority,
        "phase_policy": asset_record["phase_policy"],
        "runtime_actions_allowed_now": False,
        "download_allowed_now": False,
        "install_allowed_now": False,
        "vendor_code_allowed_now": False,
        "verdict_authority": False,
        "notes": _optional_str(audit.get("notes"), "notes"),
        "note": (
            "README audit fact record only; no runtime, download, install, "
            "vendor, external DB, or verdict authority."
        ),
    }


def _normalize_observed(value: Any) -> dict[str, Any]:
    observed = _mapping(value, "observed")
    _reject_unknown_nested_fields(
        observed,
        set(_REQUIRED_OBSERVED_FIELDS),
        "observed",
    )
    missing = [field for field in _REQUIRED_OBSERVED_FIELDS if field not in observed]
    if missing:
        raise ExternalRepoReadmeAuditValidationError(
            "observed missing required fields: " + ", ".join(missing)
        )
    return {
        "license": _required_str(observed["license"], "observed.license"),
        "runtime": _required_str(observed["runtime"], "observed.runtime"),
        "input_format": _required_str(
            observed["input_format"], "observed.input_format"
        ),
        "output_or_evidence": _required_str(
            observed["output_or_evidence"], "observed.output_or_evidence"
        ),
        "can_run_offline": _bool_or_unknown(
            observed["can_run_offline"], "observed.can_run_offline"
        ),
        "requires_network": _bool(observed["requires_network"], "observed.requires_network"),
        "requires_docker": _bool(observed["requires_docker"], "observed.requires_docker"),
        "requires_model_or_api_key": _bool(
            observed["requires_model_or_api_key"],
            "observed.requires_model_or_api_key",
        ),
        "writes_workspace": _bool(observed["writes_workspace"], "observed.writes_workspace"),
        "secrets_or_payload_risk": _bool(
            observed["secrets_or_payload_risk"],
            "observed.secrets_or_payload_risk",
        ),
    }


def _normalize_project_fit(value: Any) -> dict[str, Any]:
    project_fit = _mapping(value, "project_fit")
    _reject_unknown_nested_fields(
        project_fit,
        set(_REQUIRED_PROJECT_FIT_FIELDS),
        "project_fit",
    )
    missing = [field for field in _REQUIRED_PROJECT_FIT_FIELDS if field not in project_fit]
    if missing:
        raise ExternalRepoReadmeAuditValidationError(
            "project_fit missing required fields: " + ", ".join(missing)
        )
    fit = _required_str(project_fit["fit"], "project_fit.fit")
    if fit not in _AUDIT_FITS:
        allowed = ", ".join(sorted(_AUDIT_FITS))
        raise ExternalRepoReadmeAuditValidationError(
            f"project_fit.fit must be one of: {allowed}"
        )
    return {
        "fit": fit,
        "affects_artifact": _required_str(
            project_fit["affects_artifact"],
            "project_fit.affects_artifact",
        ),
        "expected_evidence": _string_list(
            project_fit["expected_evidence"],
            "project_fit.expected_evidence",
        ),
        "risks": _string_list(project_fit["risks"], "project_fit.risks"),
        "next_action": _required_str(project_fit["next_action"], "project_fit.next_action"),
    }


def _normalize_authority(value: Any) -> dict[str, bool]:
    authority = _mapping(value, "authority")
    _reject_unknown_nested_fields(authority, set(_AUTHORITY_FIELDS), "authority")
    missing = [field for field in _AUTHORITY_FIELDS if field not in authority]
    if missing:
        raise ExternalRepoReadmeAuditValidationError(
            "authority missing required fields: " + ", ".join(missing)
        )
    normalized: dict[str, bool] = {}
    for field in _AUTHORITY_FIELDS:
        normalized[field] = _bool(authority[field], f"authority.{field}")
        if normalized[field] is not False:
            raise ExternalRepoReadmeAuditValidationError(
                f"authority.{field} must be false for README audit records"
            )
    return normalized


def _reject_unknown_audit_fields(audit: Mapping[str, Any]) -> None:
    allowed = set(_REQUIRED_AUDIT_FIELDS) | set(_OPTIONAL_AUDIT_FIELDS)
    unknown = sorted(str(key) for key in audit if str(key) not in allowed)
    if unknown:
        raise ExternalRepoReadmeAuditValidationError(
            "external repo README audit has unknown fields: " + ", ".join(unknown)
        )


def _reject_unknown_nested_fields(
    value: Mapping[str, Any],
    allowed: set[str],
    name: str,
) -> None:
    unknown = sorted(str(key) for key in value if str(key) not in allowed)
    if unknown:
        raise ExternalRepoReadmeAuditValidationError(
            f"{name} has unknown fields: " + ", ".join(unknown)
        )


def _reject_forbidden_audit_fields(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_AUDIT_KEYS:
                raise ExternalRepoReadmeAuditValidationError(
                    "external repo README audit must not contain authority, raw "
                    f"payload, or secret field: {child_path}"
                )
            _reject_forbidden_audit_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_audit_fields(child, f"{path}[{index}]")


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalRepoReadmeAuditValidationError(f"{name} must be a mapping")
    return value


def _required_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalRepoReadmeAuditValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ExternalRepoReadmeAuditValidationError(f"{name} must be a string")
    stripped = value.strip()
    return stripped or None


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ExternalRepoReadmeAuditValidationError(f"{name} must be a list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ExternalRepoReadmeAuditValidationError(
                f"{name}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    if not normalized:
        raise ExternalRepoReadmeAuditValidationError(f"{name} must not be empty")
    return normalized


def _bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ExternalRepoReadmeAuditValidationError(f"{name} must be boolean")


def _bool_or_unknown(value: Any, name: str) -> bool | None:
    if value == "unknown" or value is None:
        return None
    return _bool(value, name)


def _iso_date(value: Any, name: str) -> str:
    text = _required_str(value, name)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ExternalRepoReadmeAuditValidationError(f"{name} must be ISO-8601 date") from exc
    return text


def _url_looks_secret_bearing(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _SECRET_URL_MARKERS)
