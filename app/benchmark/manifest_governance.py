"""Golden Set benchmark-manifest governance helpers.

S5B is a design-time gate for external benchmark seeds. It accepts
``manifest_seed`` metadata only: no dataset content, external execution,
downloads, install steps, headline metrics, or verdict authority.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date
from typing import Any, Iterable, Mapping

from app.governance.external_assets import external_asset_intake_policy

GOLDEN_MANIFEST_SEED_SCHEMA_VERSION = "golden_manifest_seed.v1"
GOLDEN_MANIFEST_GOVERNANCE_PLAN_VERSION = "golden_manifest_governance_plan.v1"
GOLDEN_DEFECT_DENOMINATOR_READINESS_VERSION = "golden_defect_denominator_readiness.v1"

SMALL_SEED_TASK_LIMIT = 5
_DEFECT_DENOMINATOR_HINTS = (
    "bug",
    "defect",
    "failing",
    "fixed",
    "verifier",
    "seeded",
)

ALLOWED_GOLDEN_CANDIDATE_KINDS = (
    "junit_unit_candidate",
    "junit_api_candidate",
    "api_schema_candidate",
    "api_collection_candidate",
    "integration_flow_candidate",
)

_REQUIRED_SEED_FIELDS = (
    "asset_id",
    "intake_shape",
    "project_artifact",
    "source_url",
    "pinned_version_or_commit",
    "license_spdx",
    "task_count_requested",
    "candidate_kind",
    "expected_evidence",
    "requires_network",
    "requires_docker",
    "requires_model_or_api_key",
    "red_lines",
    "next_action",
)

_OPTIONAL_SEED_FIELDS = (
    "schema_version",
    "license_verified_at",
    "runtime_language",
    "risk_bucket",
    "task_ids",
    "readme_audit_ref",
    "owner_gate_ref",
    "notes",
)

_FORBIDDEN_SEED_KEYS = {
    ".env",
    "accepted",
    "api_key",
    "authorization",
    "auto_accept",
    "auto_accepted",
    "auto_merge",
    "auto_warehouse",
    "candidate_code",
    "candidate_source",
    "case_content",
    "case_files",
    "cases",
    "content",
    "cookie",
    "credentials",
    "database_dump",
    "dataset",
    "dataset_content",
    "expected_metric",
    "expected_score",
    "headline_metric",
    "metric_claim",
    "model_output",
    "password",
    "payload",
    "raw_payload",
    "raw_request",
    "raw_response",
    "request_body",
    "response_body",
    "secret",
    "secrets",
    "source_code",
    "test_code",
    "tests",
    "token",
    "trusted",
    "verdict",
    "verdict_authority",
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


class GoldenManifestSeedValidationError(ValueError):
    """Raised when a Golden Set manifest seed violates S5B governance."""


def validate_golden_manifest_seed(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one metadata-only Golden Set seed.

    The returned record can be stored in a draft manifest or registry note. It
    never grants permission to download a dataset, run a tool, start a service,
    compute headline metrics, or accept a candidate.
    """
    if not isinstance(record, Mapping):
        raise GoldenManifestSeedValidationError(
            "golden manifest seed must be a mapping"
        )

    _reject_forbidden_seed_fields(record)
    _reject_unknown_seed_fields(record)

    missing = [field for field in _REQUIRED_SEED_FIELDS if field not in record]
    if missing:
        raise GoldenManifestSeedValidationError(
            "golden manifest seed missing required fields: " + ", ".join(missing)
        )

    data = deepcopy(dict(record))
    schema_version = _optional_str(
        data.get("schema_version", GOLDEN_MANIFEST_SEED_SCHEMA_VERSION),
        "schema_version",
    )
    if schema_version != GOLDEN_MANIFEST_SEED_SCHEMA_VERSION:
        raise GoldenManifestSeedValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    intake_shape = _required_str(data["intake_shape"], "intake_shape")
    if intake_shape != "manifest_seed":
        raise GoldenManifestSeedValidationError(
            "golden manifest seed requires intake_shape=manifest_seed"
        )
    phase_policy = external_asset_intake_policy(intake_shape)

    project_artifact = _required_str(data["project_artifact"], "project_artifact")
    if not _is_allowed_project_artifact(project_artifact):
        raise GoldenManifestSeedValidationError(
            "project_artifact must be a benchmark manifest draft or external registry entry"
        )

    source_url = _required_str(data["source_url"], "source_url")
    if not source_url.startswith(("https://", "http://")):
        raise GoldenManifestSeedValidationError(
            "source_url must be an http(s) URL for external manifest seeds"
        )
    if _url_looks_secret_bearing(source_url):
        raise GoldenManifestSeedValidationError(
            "source_url must not contain secret-like query parameters"
        )

    task_count_requested = _positive_int(
        data["task_count_requested"],
        "task_count_requested",
    )
    task_ids = _optional_string_list(data.get("task_ids"), "task_ids")
    if task_ids and len(task_ids) > task_count_requested:
        raise GoldenManifestSeedValidationError(
            "task_ids must not exceed task_count_requested"
        )

    candidate_kind = _required_str(data["candidate_kind"], "candidate_kind")
    if candidate_kind not in ALLOWED_GOLDEN_CANDIDATE_KINDS:
        allowed = ", ".join(ALLOWED_GOLDEN_CANDIDATE_KINDS)
        raise GoldenManifestSeedValidationError(
            f"candidate_kind must be one of: {allowed}"
        )

    requires_network = _bool(data["requires_network"], "requires_network")
    requires_docker = _bool(data["requires_docker"], "requires_docker")
    requires_model_or_api_key = _bool(
        data["requires_model_or_api_key"],
        "requires_model_or_api_key",
    )
    future_owner_gate_reasons = _future_owner_gate_reasons(
        task_count_requested=task_count_requested,
        requires_network=requires_network,
        requires_docker=requires_docker,
        requires_model_or_api_key=requires_model_or_api_key,
    )

    return {
        "schema_version": schema_version,
        "asset_id": _required_str(data["asset_id"], "asset_id"),
        "intake_shape": intake_shape,
        "project_artifact": project_artifact,
        "source_url": source_url,
        "pinned_version_or_commit": _required_str(
            data["pinned_version_or_commit"],
            "pinned_version_or_commit",
        ),
        "license_spdx": _required_str(data["license_spdx"], "license_spdx"),
        "license_verified_at": _optional_iso_date(
            data.get("license_verified_at"),
            "license_verified_at",
        ),
        "runtime_language": _optional_str(
            data.get("runtime_language"),
            "runtime_language",
        ),
        "task_count_requested": task_count_requested,
        "task_ids": task_ids,
        "candidate_kind": candidate_kind,
        "expected_evidence": _string_list(
            data["expected_evidence"],
            "expected_evidence",
        ),
        "requires_network": requires_network,
        "requires_docker": requires_docker,
        "requires_model_or_api_key": requires_model_or_api_key,
        "red_lines": _string_list(data["red_lines"], "red_lines"),
        "next_action": _required_str(data["next_action"], "next_action"),
        "risk_bucket": _optional_str(data.get("risk_bucket"), "risk_bucket"),
        "readme_audit_ref": _optional_str(
            data.get("readme_audit_ref"),
            "readme_audit_ref",
        ),
        "owner_gate_ref": _optional_str(data.get("owner_gate_ref"), "owner_gate_ref"),
        "notes": _optional_str(data.get("notes"), "notes"),
        "phase_policy": _phase_summary(phase_policy),
        "metadata_only": True,
        "golden_manifest_draft_allowed_now": True,
        "small_seed_policy_ok": task_count_requested <= SMALL_SEED_TASK_LIMIT,
        "future_owner_gate_reasons": future_owner_gate_reasons,
        "owner_gate_required_before_dataset_slice": True,
        "runtime_actions_allowed_now": False,
        "download_allowed_now": False,
        "install_allowed_now": False,
        "benchmark_headline_allowed_now": False,
        "verdict_authority": False,
        "note": (
            "Metadata-only Golden Set seed. This is not permission to download, "
            "install, execute, import dataset rows, compute headline metrics, or "
            "change candidate verdicts."
        ),
    }


def golden_manifest_governance_plan(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate and summarize Golden Set manifest seeds.

    The plan is a preflight for a future manifest draft. It summarizes where
    owner gates will be required, while all runtime and verdict authority stays
    false.
    """
    normalized = [validate_golden_manifest_seed(record) for record in records]
    _reject_duplicate_asset_ids(normalized)

    runtime_risk_records = [
        record["asset_id"]
        for record in normalized
        if record["requires_network"]
        or record["requires_docker"]
        or record["requires_model_or_api_key"]
    ]
    large_seed_request_records = [
        record["asset_id"]
        for record in normalized
        if record["task_count_requested"] > SMALL_SEED_TASK_LIMIT
    ]
    future_owner_gated_records = [
        record["asset_id"]
        for record in normalized
        if record["future_owner_gate_reasons"]
    ]

    return {
        "plan_version": GOLDEN_MANIFEST_GOVERNANCE_PLAN_VERSION,
        "seed_schema_version": GOLDEN_MANIFEST_SEED_SCHEMA_VERSION,
        "total_records": len(normalized),
        "metadata_only_records": [record["asset_id"] for record in normalized],
        "golden_manifest_draft_records": [
            record["asset_id"]
            for record in normalized
            if record["golden_manifest_draft_allowed_now"] is True
        ],
        "small_seed_policy_ok_records": [
            record["asset_id"]
            for record in normalized
            if record["small_seed_policy_ok"] is True
        ],
        "large_seed_request_records": large_seed_request_records,
        "future_owner_gated_records": future_owner_gated_records,
        "runtime_risk_records": runtime_risk_records,
        "by_candidate_kind": _counter_dict(
            record["candidate_kind"] for record in normalized
        ),
        "by_project_artifact": _counter_dict(
            record["project_artifact"] for record in normalized
        ),
        "runtime_actions_allowed_records": [],
        "download_allowed_records": [],
        "install_allowed_records": [],
        "benchmark_headline_allowed_records": [],
        "verdict_authority_records": [],
        "records": [_compact_plan_record(record) for record in normalized],
        "note": (
            "S5B governance summary only. A seed can enter metadata planning, "
            "but dataset materialization, external execution, headline metrics, "
            "and verdict authority remain owner-gated or forbidden."
        ),
    }


def golden_defect_denominator_readiness(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize whether Golden Set seeds could later support defect metrics.

    This is metadata-only readiness. It never materializes a dataset slice,
    executes a verifier, changes benchmark headlines, or grants verdict/trust
    authority.
    """
    normalized = [validate_golden_manifest_seed(record) for record in records]
    _reject_duplicate_asset_ids(normalized)

    candidates = [
        record for record in normalized if _looks_like_defect_denominator_seed(record)
    ]
    pinned_task_id_count = sum(len(record["task_ids"]) for record in candidates)
    requested_task_count = sum(record["task_count_requested"] for record in candidates)
    future_owner_gated_records = [
        record["asset_id"]
        for record in candidates
        if record["future_owner_gate_reasons"]
    ]

    return {
        "schema_version": GOLDEN_DEFECT_DENOMINATOR_READINESS_VERSION,
        "seed_schema_version": GOLDEN_MANIFEST_SEED_SCHEMA_VERSION,
        "advisory": True,
        "metadata_only": True,
        "total_seed_records": len(normalized),
        "defect_denominator_candidate_records": [
            record["asset_id"] for record in candidates
        ],
        "requested_task_count": requested_task_count,
        "pinned_task_id_count": pinned_task_id_count,
        "small_seed_policy_ok_records": [
            record["asset_id"]
            for record in candidates
            if record["small_seed_policy_ok"] is True
        ],
        "future_owner_gated_records": future_owner_gated_records,
        "future_defect_denominator_possible": bool(candidates),
        "defect_denominator_ready_now": False,
        "defect_discovery_rate_value": None,
        "not_ready_reasons": _defect_denominator_not_ready_reasons(
            candidates=candidates,
            pinned_task_id_count=pinned_task_id_count,
        ),
        "dataset_materialization_allowed_now": False,
        "download_allowed_now": False,
        "external_execution_allowed_now": False,
        "verifier_execution_allowed_now": False,
        "benchmark_headline_allowed_now": False,
        "defect_discovery_rate_authority": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "records": [
            {
                "asset_id": record["asset_id"],
                "candidate_kind": record["candidate_kind"],
                "task_count_requested": record["task_count_requested"],
                "task_ids": list(record["task_ids"]),
                "future_owner_gate_reasons": list(record["future_owner_gate_reasons"]),
                "defect_denominator_candidate": record in candidates,
            }
            for record in normalized
        ],
        "note": (
            "Golden Set defect denominator readiness is metadata only. It can "
            "identify future denominator candidates, but defect-discovery rates "
            "remain unavailable until an owner-gated dataset slice and verifier "
            "evidence exist."
        ),
    }


def _future_owner_gate_reasons(
    *,
    task_count_requested: int,
    requires_network: bool,
    requires_docker: bool,
    requires_model_or_api_key: bool,
) -> list[str]:
    reasons: list[str] = ["dataset_slice_materialization"]
    if task_count_requested > SMALL_SEED_TASK_LIMIT:
        reasons.append("task_count_exceeds_small_seed_limit")
    if requires_network:
        reasons.append("network_required")
    if requires_docker:
        reasons.append("docker_required")
    if requires_model_or_api_key:
        reasons.append("model_or_api_key_required")
    return reasons


def _looks_like_defect_denominator_seed(record: Mapping[str, Any]) -> bool:
    text = " ".join([
        str(record.get("asset_id") or ""),
        str(record.get("source_url") or ""),
        str(record.get("risk_bucket") or ""),
        " ".join(str(item) for item in record.get("task_ids") or []),
        " ".join(str(item) for item in record.get("expected_evidence") or []),
        str(record.get("notes") or ""),
    ]).lower()
    return any(hint in text for hint in _DEFECT_DENOMINATOR_HINTS)


def _defect_denominator_not_ready_reasons(
    *,
    candidates: list[Mapping[str, Any]],
    pinned_task_id_count: int,
) -> list[str]:
    if not candidates:
        return ["no_defect_denominator_manifest_seed"]
    reasons = [
        "dataset_slice_materialization_owner_gate_required",
        "verifier_execution_not_live",
        "benchmark_headline_not_allowed_from_metadata",
    ]
    if pinned_task_id_count <= 0:
        reasons.append("pinned_task_ids_missing")
    return reasons


def _phase_summary(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_version": policy["policy_version"],
        "earliest_stage": policy["earliest_stage"],
        "current_status": policy["current_status"],
        "allowed_now": list(policy["allowed_now"]),
        "owner_gate_before": list(policy["owner_gate_before"]),
        "global_red_lines": list(policy["global_red_lines"]),
    }


def _compact_plan_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": record["asset_id"],
        "candidate_kind": record["candidate_kind"],
        "project_artifact": record["project_artifact"],
        "task_count_requested": record["task_count_requested"],
        "small_seed_policy_ok": record["small_seed_policy_ok"],
        "future_owner_gate_reasons": list(record["future_owner_gate_reasons"]),
        "requires_network": record["requires_network"],
        "requires_docker": record["requires_docker"],
        "requires_model_or_api_key": record["requires_model_or_api_key"],
        "runtime_actions_allowed_now": record["runtime_actions_allowed_now"],
        "download_allowed_now": record["download_allowed_now"],
        "install_allowed_now": record["install_allowed_now"],
        "benchmark_headline_allowed_now": record["benchmark_headline_allowed_now"],
        "verdict_authority": record["verdict_authority"],
    }


def _reject_duplicate_asset_ids(records: list[Mapping[str, Any]]) -> None:
    counts = Counter(record["asset_id"] for record in records)
    duplicates = sorted(asset_id for asset_id, count in counts.items() if count > 1)
    if duplicates:
        raise GoldenManifestSeedValidationError(
            "golden manifest seeds contain duplicate asset_id values: "
            + ", ".join(duplicates)
        )


def _reject_unknown_seed_fields(record: Mapping[str, Any]) -> None:
    allowed = set(_REQUIRED_SEED_FIELDS) | set(_OPTIONAL_SEED_FIELDS)
    unknown = sorted(str(key) for key in record if str(key) not in allowed)
    if unknown:
        raise GoldenManifestSeedValidationError(
            "golden manifest seed has unknown fields: " + ", ".join(unknown)
        )


def _reject_forbidden_seed_fields(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_SEED_KEYS:
                raise GoldenManifestSeedValidationError(
                    "golden manifest seed must not contain authority, dataset "
                    f"content, raw payload, or secret field: {child_path}"
                )
            _reject_forbidden_seed_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_seed_fields(child, f"{path}[{index}]")


def _is_allowed_project_artifact(value: str) -> bool:
    return (
        value.startswith("benchmarks/")
        or value == "docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md"
    )


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values).most_common())


def _required_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GoldenManifestSeedValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise GoldenManifestSeedValidationError(f"{name} must be a string")
    stripped = value.strip()
    return stripped or None


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise GoldenManifestSeedValidationError(f"{name} must be a list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise GoldenManifestSeedValidationError(
                f"{name}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    if not normalized:
        raise GoldenManifestSeedValidationError(f"{name} must not be empty")
    return normalized


def _optional_string_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    return _string_list(value, name)


def _bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise GoldenManifestSeedValidationError(f"{name} must be boolean")


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GoldenManifestSeedValidationError(f"{name} must be an integer")
    if value <= 0:
        raise GoldenManifestSeedValidationError(f"{name} must be > 0")
    return value


def _optional_iso_date(value: Any, name: str) -> str | None:
    if value is None:
        return None
    text = _required_str(value, name)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise GoldenManifestSeedValidationError(
            f"{name} must be ISO-8601 date"
        ) from exc
    return text


def _url_looks_secret_bearing(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _SECRET_URL_MARKERS)
