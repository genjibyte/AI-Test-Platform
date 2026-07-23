"""External asset phase gates.

These helpers encode the docs/knowledge external-asset intake ladder as pure
policy data. They do not clone, install, connect, execute, or authorize use of
any external asset.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date
from typing import Any, Iterable, Mapping

EXTERNAL_ASSET_PHASE_POLICY_VERSION = "external_asset_phase_policy.v1"
EXTERNAL_ASSET_RECORD_SCHEMA_VERSION = "external_asset_record.v1"
EXTERNAL_ASSET_INTAKE_PLAN_VERSION = "external_asset_intake_plan.v1"
DESIGN_REUSE_CHECK_SCHEMA_VERSION = "design_reuse_check.v1"
DESIGN_REUSE_CHECK_PLAN_VERSION = "design_reuse_check_plan.v1"
KNOWLEDGE_EMBEDDING_DESTINATION_VERSION = "knowledge_embedding_destination.v1"

_CURRENT_MAINLINE_STATUS = (
    "S10B live: API smoke report/submit/benchmark/ledger projections only; "
    "no external executor, dataset slice, service orchestration, external DB, "
    "or vendored code."
)

_GLOBAL_RED_LINES = (
    "no_auto_accept_or_trusted_true",
    "no_bulk_import",
    "no_project_tree_vendor_copy",
    "no_external_execution_without_owner_gate",
    "no_external_database_connection_without_owner_gate",
    "no_model_or_api_call_without_cost_approval",
    "no_historical_benchmark_backfill",
    "no_existing_headline_metric_drift",
)

_REQUIRED_RECORD_FIELDS = (
    "asset_id",
    "source_url",
    "intake_shape",
    "project_artifact",
    "pinned_version_or_commit",
    "license_spdx",
    "license_verified_at",
    "runtime_language",
    "requires_network",
    "requires_docker",
    "writes_workspace",
    "secrets_or_payload_risk",
    "expected_evidence",
    "red_lines",
    "next_action",
)

_OPTIONAL_RECORD_FIELDS = (
    "schema_version",
    "owner_gate_ref",
    "readme_audit_ref",
    "notes",
)

_REQUIRED_REUSE_CHECK_FIELDS = (
    "design_topic",
    "source_family",
    "source_ref",
    "intake_shape",
    "project_artifact",
    "reuse_decision",
    "expected_evidence",
    "red_lines",
    "boundary",
)

_OPTIONAL_REUSE_CHECK_FIELDS = (
    "schema_version",
    "owner_gate_ref",
    "notes",
)

_REUSE_SOURCE_FAMILIES = {
    "curated_knowledge_base",
    "external_project_registry",
    "paper_or_article",
    "tool_or_framework",
    "evaluation_set",
    "existing_code_pattern",
}

_FORBIDDEN_RECORD_KEYS = {
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

_FORBIDDEN_REUSE_KEYS = _FORBIDDEN_RECORD_KEYS | {
    "clone_command",
    "copy_path",
    "database_url",
    "dependency_to_add",
    "download_command",
    "execute_command",
    "install_command",
    "run_command",
    "vendor_path",
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

_INTAKE_POLICIES: dict[str, dict[str, Any]] = {
    "knowledge_note": {
        "earliest_stage": "S5D",
        "current_status": "allowed_now_documentation_only",
        "allowed_now": (
            "curate_design_lesson",
            "record_warning_or_vocabulary",
            "link_to_active_design_doc",
        ),
        "project_artifact": "docs/knowledge curated note or task design section",
        "owner_gate_before": ("runtime_use", "dependency", "dataset_slice"),
        "next_gate": "source facts must be reconciled against active docs before use",
    },
    "readme_audit": {
        "earliest_stage": "S5B0",
        "current_status": "allowed_now_audit_only",
        "allowed_now": (
            "focused_readme_license_runtime_audit",
            "scratch_read_only_checkout_outside_project_tree",
            "record_asset_block",
        ),
        "project_artifact": "docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",
        "owner_gate_before": ("install", "execute", "vendor_code", "adapter_code"),
        "next_gate": "bounded design must name candidate kind, evidence, and isolation",
    },
    "manifest_seed": {
        "earliest_stage": "S5B",
        "current_status": "design_allowed_metadata_only",
        "allowed_now": (
            "pin_url_commit_tag_task_id",
            "record_license_runtime_risk",
            "declare_expected_evidence",
        ),
        "project_artifact": "new benchmark manifest draft or external registry entry",
        "owner_gate_before": ("download_data", "execute_case", "headline_metric"),
        "next_gate": "golden-set governance must approve the manifest version",
    },
    "dataset_slice": {
        "earliest_stage": "S11",
        "current_status": "future_owner_gated",
        "allowed_now": (),
        "project_artifact": "tiny pinned golden-set or defect-seed slice",
        "owner_gate_before": ("any_download", "any_extraction", "any_execution"),
        "next_gate": "3-5 pinned cases, license verified, no bulk import",
    },
    "producer_adapter": {
        "earliest_stage": "S12",
        "current_status": "future_owner_gated",
        "allowed_now": (),
        "project_artifact": "candidate input adapter feeding submit_candidate",
        "owner_gate_before": ("tool_invocation", "dependency", "generated_output_claim"),
        "next_gate": "adapter output must enter the same judge/report path",
    },
    "executor_adapter": {
        "earliest_stage": "S13",
        "current_status": "future_owner_gated",
        "allowed_now": (),
        "project_artifact": "isolated runner plus compact evidence parser",
        "owner_gate_before": ("install", "execute", "service_start", "network_access"),
        "next_gate": "candidate kind, command, parser, isolation, and no-verdict-drift tests",
    },
    "sut_target": {
        "earliest_stage": "S7C",
        "current_status": "reference_allowed_after_readme_audit",
        "allowed_now": (
            "record_name_url_commit_readme_audit_ref",
            "reference_in_api_smoke_manifest",
        ),
        "project_artifact": "api_smoke_manifest target.sut_ref",
        "owner_gate_before": ("clone_for_execution", "service_orchestration", "docker"),
        "next_gate": "API/integration runner design before live SUT execution",
    },
    "isolation_support": {
        "earliest_stage": "S13",
        "current_status": "future_owner_gated",
        "allowed_now": (),
        "project_artifact": "mock/container/contract support for API or integration runner",
        "owner_gate_before": ("dependency", "docker", "service_start"),
        "next_gate": "only after runner design proves why isolation asset is required",
    },
    "provenance_support": {
        "earliest_stage": "S12",
        "current_status": "design_allowed_metadata_only",
        "allowed_now": (
            "record_producer_trace_field_names",
            "map_to_advisory_provenance",
        ),
        "project_artifact": "producer metadata or future provenance design",
        "owner_gate_before": ("telemetry_stack", "network_export", "verdict_use"),
        "next_gate": "provenance must remain advisory and never a quality warrant",
    },
    "discovery_index": {
        "earliest_stage": "S5D",
        "current_status": "allowed_now_tracking_only",
        "allowed_now": ("record_discovery_source", "defer_asset_selection"),
        "project_artifact": "external registry note",
        "owner_gate_before": ("backlog_expansion", "implementation_task"),
        "next_gate": "selected asset still needs its own intake shape",
    },
    "support_only": {
        "earliest_stage": "future",
        "current_status": "defer",
        "allowed_now": ("retain_as_reference_name",),
        "project_artifact": "registry deferred row",
        "owner_gate_before": ("design_use", "implementation_use"),
        "next_gate": "reclassify only when a concrete judge artifact needs it",
    },
    "reject_mainline": {
        "earliest_stage": "never_as_mainline",
        "current_status": "rejected_as_architecture",
        "allowed_now": ("record_boundary_warning",),
        "project_artifact": "boundary note",
        "owner_gate_before": ("any_mainline_adoption",),
        "next_gate": "must be reframed as a bounded adapter or stay rejected",
    },
}

_CATEGORY_POLICIES: dict[str, dict[str, Any]] = {
    "external_knowledge_base": {
        "recommended_intake_shapes": ("knowledge_note", "readme_audit"),
        "earliest_stage": "S5D/S5B0",
        "current_answer": (
            "Now, but only as curated docs and README audits. It is not runtime "
            "RAG, a vector DB, or project truth."
        ),
        "not_before": ("runtime_rag", "knowledge_graph", "model_judge_authority"),
    },
    "external_benchmark_dataset": {
        "recommended_intake_shapes": ("readme_audit", "manifest_seed", "dataset_slice"),
        "earliest_stage": "S5B for metadata, S11 for tiny slice",
        "current_answer": (
            "Metadata can enter during Golden Set governance. Actual examples "
            "or defect seeds wait for an owner-approved tiny pinned slice."
        ),
        "not_before": ("bulk_download", "headline_metric", "historical_backfill"),
    },
    "open_source_tool_code": {
        "recommended_intake_shapes": (
            "readme_audit",
            "producer_adapter",
            "executor_adapter",
            "isolation_support",
        ),
        "earliest_stage": "S5B0 for audit, S12/S13 for adapters",
        "current_answer": (
            "Audit now; run through a producer or executor adapter later. Do "
            "not copy tool code into the repo as the default integration path."
        ),
        "not_before": ("install", "execute", "vendor_code", "new_dependency"),
    },
    "external_database": {
        "recommended_intake_shapes": ("knowledge_note", "manifest_seed", "sut_target"),
        "earliest_stage": "S11+ depending on role",
        "current_answer": (
            "As a SUT schema/fixture it belongs to future API/integration asset "
            "gates; as platform storage it waits until local ledger/report scale "
            "requires a new backend."
        ),
        "not_before": (
            "external_storage_backend",
            "service_connection",
            "database_dump",
            "runtime_secrets",
        ),
    },
}

_KNOWLEDGE_EMBEDDING_DESTINATIONS: dict[str, dict[str, Any]] = {
    "knowledge_note": {
        "summary_shape": "short design lesson, metric, warning, or vocabulary note",
        "primary_docs": (
            "task-routed design doc",
            "docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md",
        ),
        "secondary_docs": ("docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",),
        "project_artifact": "curated knowledge note or bounded design section",
    },
    "readme_audit": {
        "summary_shape": "focused README/license/runtime fact block",
        "primary_docs": ("docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",),
        "secondary_docs": ("docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",),
        "project_artifact": "external README audit record",
    },
    "manifest_seed": {
        "summary_shape": "pinned metadata record, not dataset content",
        "primary_docs": (
            "docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",
            "docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md",
        ),
        "secondary_docs": ("docs/50_benchmark/23_BENCHMARK_MANIFEST.md",),
        "project_artifact": "metadata-only manifest seed or registry row",
    },
    "dataset_slice": {
        "summary_shape": "owner-gated tiny slice design, not imported rows",
        "primary_docs": ("docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md",),
        "secondary_docs": ("docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",),
        "project_artifact": "future pinned golden-set or defect-seed slice design",
    },
    "producer_adapter": {
        "summary_shape": "candidate-input adapter design note",
        "primary_docs": (
            "docs/50_benchmark/53_SUBMIT_CANDIDATE_DESIGN.md",
            "docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md",
        ),
        "secondary_docs": ("docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",),
        "project_artifact": "future producer adapter feeding submit_candidate",
    },
    "executor_adapter": {
        "summary_shape": "runner command, evidence parser, and isolation design note",
        "primary_docs": (
            "docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md",
            "docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md",
        ),
        "secondary_docs": ("docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",),
        "project_artifact": "future owner-gated executor adapter design",
    },
    "sut_target": {
        "summary_shape": "SUT reference metadata for smoke-manifest design",
        "primary_docs": (
            "docs/60_api_candidate/07_S7C_JUNIT_API_SMOKE_MANIFEST_DESIGN.md",
            "docs/60_api_candidate/08_S7D_API_SMOKE_MANIFEST_CARRY_THROUGH_DESIGN.md",
        ),
        "secondary_docs": (
            "docs/60_api_candidate/09_S8_API_SMOKE_DENOMINATOR_POLICY.md",
            "docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",
        ),
        "project_artifact": "api_smoke_manifest target.sut_ref",
    },
    "isolation_support": {
        "summary_shape": "mock/container/contract isolation design note",
        "primary_docs": ("docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md",),
        "secondary_docs": (
            "docs/knowledge/EXTERNAL_REPO_README_AUDIT.md",
            "docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",
        ),
        "project_artifact": "future API/integration isolation design",
    },
    "provenance_support": {
        "summary_shape": "advisory producer trace and run-kind field mapping",
        "primary_docs": (
            "docs/50_benchmark/53_SUBMIT_CANDIDATE_DESIGN.md",
            "docs/50_benchmark/43_RUN_KIND_DESIGN.md",
        ),
        "secondary_docs": ("docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",),
        "project_artifact": "producer metadata or future provenance design",
    },
    "discovery_index": {
        "summary_shape": "compact registry row or discovery source note",
        "primary_docs": ("docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",),
        "secondary_docs": ("docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md",),
        "project_artifact": "external registry row",
    },
    "support_only": {
        "summary_shape": "deferred reference row with a concrete revisit trigger",
        "primary_docs": ("docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",),
        "secondary_docs": ("docs/knowledge/README.md",),
        "project_artifact": "registry deferred row",
    },
    "reject_mainline": {
        "summary_shape": "boundary warning explaining why it is not mainline",
        "primary_docs": ("docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md",),
        "secondary_docs": ("docs/knowledge/README.md",),
        "project_artifact": "boundary note",
    },
}


class ExternalAssetPolicyError(ValueError):
    """Raised when an unknown external asset intake shape/category is requested."""


class ExternalAssetRecordValidationError(ValueError):
    """Raised when an external asset record violates the governance contract."""


class DesignReuseCheckValidationError(ValueError):
    """Raised when a design input misses the mandatory reuse-check contract."""


def external_asset_intake_policy(intake_shape: str) -> dict[str, Any]:
    """Return the phase gate for one intake shape.

    The returned dict is a defensive copy so callers cannot mutate module policy.
    """
    if intake_shape not in _INTAKE_POLICIES:
        allowed = ", ".join(sorted(_INTAKE_POLICIES))
        raise ExternalAssetPolicyError(
            f"unknown external asset intake_shape {intake_shape!r}; allowed: {allowed}"
        )
    policy = deepcopy(_INTAKE_POLICIES[intake_shape])
    policy.update({
        "policy_version": EXTERNAL_ASSET_PHASE_POLICY_VERSION,
        "intake_shape": intake_shape,
        "current_mainline_status": _CURRENT_MAINLINE_STATUS,
        "global_red_lines": list(_GLOBAL_RED_LINES),
    })
    return policy


def external_asset_category_policy(category: str) -> dict[str, Any]:
    """Return the stage answer for a user-facing external asset category."""
    if category not in _CATEGORY_POLICIES:
        allowed = ", ".join(sorted(_CATEGORY_POLICIES))
        raise ExternalAssetPolicyError(
            f"unknown external asset category {category!r}; allowed: {allowed}"
        )
    policy = deepcopy(_CATEGORY_POLICIES[category])
    policy.update({
        "policy_version": EXTERNAL_ASSET_PHASE_POLICY_VERSION,
        "category": category,
        "current_mainline_status": _CURRENT_MAINLINE_STATUS,
        "global_red_lines": list(_GLOBAL_RED_LINES),
    })
    return policy


def knowledge_embedding_destination(intake_shape: str) -> dict[str, Any]:
    """Return where a new external-knowledge summary belongs.

    This is a documentation router only. It helps a design decide which docs to
    update after classifying an external asset, but it grants no authority to
    clone, copy, install, vendor, execute, connect, or change verdict/trust.
    """
    phase_policy = external_asset_intake_policy(intake_shape)
    if intake_shape not in _KNOWLEDGE_EMBEDDING_DESTINATIONS:
        raise ExternalAssetPolicyError(
            f"intake_shape {intake_shape!r} has no knowledge embedding destination"
        )
    destination = deepcopy(_KNOWLEDGE_EMBEDDING_DESTINATIONS[intake_shape])
    return {
        "destination_version": KNOWLEDGE_EMBEDDING_DESTINATION_VERSION,
        "intake_shape": intake_shape,
        "summary_shape": destination["summary_shape"],
        "primary_docs": list(destination["primary_docs"]),
        "secondary_docs": list(destination["secondary_docs"]),
        "project_artifact": destination["project_artifact"],
        "phase_policy": _record_phase_summary(phase_policy),
        "runtime_actions_allowed_now": False,
        "download_allowed_now": False,
        "install_allowed_now": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "note": (
            "Documentation routing only. Summarize the source into the named "
            "docs/artifact and keep external execution, dependencies, data "
            "imports, verdict authority, and trusted status owner-gated."
        ),
    }


def validate_external_asset_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a design-time external asset record block.

    The record is metadata only. A valid record never authorizes download,
    installation, external execution, database connection, or vendored code.
    """
    if not isinstance(record, Mapping):
        raise ExternalAssetRecordValidationError("external asset record must be a mapping")

    _reject_record_forbidden_fields(record)
    _reject_unknown_record_fields(record)

    missing = [field for field in _REQUIRED_RECORD_FIELDS if field not in record]
    if missing:
        raise ExternalAssetRecordValidationError(
            "external asset record missing required fields: " + ", ".join(missing)
        )

    schema_version = _record_optional_str(
        record.get("schema_version", EXTERNAL_ASSET_RECORD_SCHEMA_VERSION),
        "schema_version",
    )
    if schema_version != EXTERNAL_ASSET_RECORD_SCHEMA_VERSION:
        raise ExternalAssetRecordValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    source_url = _record_required_str(record["source_url"], "source_url")
    if _url_looks_secret_bearing(source_url):
        raise ExternalAssetRecordValidationError(
            "source_url must not contain secret-like query parameters"
        )

    intake_shape = _record_required_str(record["intake_shape"], "intake_shape")
    try:
        phase_policy = external_asset_intake_policy(intake_shape)
    except ExternalAssetPolicyError as exc:
        raise ExternalAssetRecordValidationError(str(exc)) from exc

    normalized = {
        "schema_version": schema_version,
        "asset_id": _record_required_str(record["asset_id"], "asset_id"),
        "source_url": source_url,
        "intake_shape": intake_shape,
        "project_artifact": _record_required_str(
            record["project_artifact"], "project_artifact"
        ),
        "pinned_version_or_commit": _record_required_str(
            record["pinned_version_or_commit"], "pinned_version_or_commit"
        ),
        "license_spdx": _record_required_str(record["license_spdx"], "license_spdx"),
        "license_verified_at": _record_iso_date(
            record["license_verified_at"], "license_verified_at"
        ),
        "runtime_language": _record_required_str(
            record["runtime_language"], "runtime_language"
        ),
        "requires_network": _record_bool(record["requires_network"], "requires_network"),
        "requires_docker": _record_bool(record["requires_docker"], "requires_docker"),
        "writes_workspace": _record_bool(record["writes_workspace"], "writes_workspace"),
        "secrets_or_payload_risk": _record_bool(
            record["secrets_or_payload_risk"], "secrets_or_payload_risk"
        ),
        "expected_evidence": _record_string_list(
            record["expected_evidence"], "expected_evidence"
        ),
        "red_lines": _record_string_list(record["red_lines"], "red_lines"),
        "next_action": _record_required_str(record["next_action"], "next_action"),
        "owner_gate_ref": _record_optional_str(
            record.get("owner_gate_ref"), "owner_gate_ref"
        ),
        "readme_audit_ref": _record_optional_str(
            record.get("readme_audit_ref"), "readme_audit_ref"
        ),
        "notes": _record_optional_str(record.get("notes"), "notes"),
        "phase_policy": _record_phase_summary(phase_policy),
        "runtime_actions_allowed_now": False,
        "download_allowed_now": False,
        "install_allowed_now": False,
        "verdict_authority": False,
    }
    return normalized


def validate_design_reuse_check(check: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the mandatory reuse check for a design input.

    This is a design preflight only. It encourages borrow/adapt from curated
    knowledge, articles, tools, evaluation sets, projects, and existing code
    patterns, but never grants permission to clone, install, execute, vendor, or
    change verdict/trust behavior.
    """
    if not isinstance(check, Mapping):
        raise DesignReuseCheckValidationError("design reuse check must be a mapping")

    _reject_reuse_forbidden_fields(check)
    _reject_unknown_reuse_fields(check)

    missing = [field for field in _REQUIRED_REUSE_CHECK_FIELDS if field not in check]
    if missing:
        raise DesignReuseCheckValidationError(
            "design reuse check missing required fields: " + ", ".join(missing)
        )

    schema_version = _reuse_optional_str(
        check.get("schema_version", DESIGN_REUSE_CHECK_SCHEMA_VERSION),
        "schema_version",
    )
    if schema_version != DESIGN_REUSE_CHECK_SCHEMA_VERSION:
        raise DesignReuseCheckValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    source_family = _reuse_required_str(check["source_family"], "source_family")
    if source_family not in _REUSE_SOURCE_FAMILIES:
        allowed = ", ".join(sorted(_REUSE_SOURCE_FAMILIES))
        raise DesignReuseCheckValidationError(
            f"unknown source_family {source_family!r}; allowed: {allowed}"
        )

    intake_shape = _reuse_required_str(check["intake_shape"], "intake_shape")
    try:
        phase_policy = external_asset_intake_policy(intake_shape)
    except ExternalAssetPolicyError as exc:
        raise DesignReuseCheckValidationError(str(exc)) from exc

    return {
        "schema_version": schema_version,
        "mandatory_for_design": True,
        "design_topic": _reuse_required_str(check["design_topic"], "design_topic"),
        "source_family": source_family,
        "source_ref": _reuse_required_str(check["source_ref"], "source_ref"),
        "intake_shape": intake_shape,
        "project_artifact": _reuse_required_str(
            check["project_artifact"], "project_artifact"
        ),
        "reuse_decision": _reuse_required_str(
            check["reuse_decision"], "reuse_decision"
        ),
        "expected_evidence": _reuse_string_list(
            check["expected_evidence"], "expected_evidence"
        ),
        "red_lines": _reuse_string_list(check["red_lines"], "red_lines"),
        "boundary": _reuse_required_str(check["boundary"], "boundary"),
        "owner_gate_ref": _reuse_optional_str(
            check.get("owner_gate_ref"), "owner_gate_ref"
        ),
        "notes": _reuse_optional_str(check.get("notes"), "notes"),
        "phase_policy": _record_phase_summary(phase_policy),
        "runtime_actions_allowed_now": False,
        "download_allowed_now": False,
        "install_allowed_now": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "note": (
            "Mandatory design reuse check only. Prefer borrow/adapt, but do not "
            "clone, copy, install, vendor, execute, connect external services, "
            "or change verdict/trust without owner-gated scope."
        ),
    }


def design_reuse_check_plan(checks: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate and summarize mandatory reuse checks for one design input.

    A non-empty plan proves the design considered reuse before inventing a new
    mechanism. It is still metadata-only and never grants runtime authority.
    """
    normalized = [validate_design_reuse_check(check) for check in checks]
    blocking_flags = [] if normalized else ["reuse_check_missing"]
    future_owner_gated_checks = [
        check["design_topic"]
        for check in normalized
        if check["phase_policy"]["current_status"] == "future_owner_gated"
    ]
    metadata_only_checks = [
        check["design_topic"]
        for check in normalized
        if check["phase_policy"]["current_status"]
        in {
            "allowed_now_documentation_only",
            "allowed_now_audit_only",
            "allowed_now_tracking_only",
            "design_allowed_metadata_only",
            "reference_allowed_after_readme_audit",
        }
    ]
    rejected_or_deferred_checks = [
        check["design_topic"]
        for check in normalized
        if check["phase_policy"]["current_status"] in {"defer", "rejected_as_architecture"}
    ]

    return {
        "plan_version": DESIGN_REUSE_CHECK_PLAN_VERSION,
        "schema_version": DESIGN_REUSE_CHECK_SCHEMA_VERSION,
        "phase_policy_version": EXTERNAL_ASSET_PHASE_POLICY_VERSION,
        "mandatory_for_design": True,
        "current_mainline_status": _CURRENT_MAINLINE_STATUS,
        "total_checks": len(normalized),
        "by_source_family": _counter_dict(check["source_family"] for check in normalized),
        "by_intake_shape": _counter_dict(check["intake_shape"] for check in normalized),
        "by_current_status": _counter_dict(
            check["phase_policy"]["current_status"] for check in normalized
        ),
        "metadata_only_checks": metadata_only_checks,
        "future_owner_gated_checks": future_owner_gated_checks,
        "rejected_or_deferred_checks": rejected_or_deferred_checks,
        "runtime_actions_allowed_checks": [
            check["design_topic"]
            for check in normalized
            if check["runtime_actions_allowed_now"] is True
        ],
        "download_allowed_checks": [
            check["design_topic"]
            for check in normalized
            if check["download_allowed_now"] is True
        ],
        "install_allowed_checks": [
            check["design_topic"]
            for check in normalized
            if check["install_allowed_now"] is True
        ],
        "verdict_authority_checks": [
            check["design_topic"]
            for check in normalized
            if check["verdict_authority"] is True
        ],
        "trusted_authority_checks": [
            check["design_topic"]
            for check in normalized
            if check["trusted_authority"] is True
        ],
        "blocking_flags": blocking_flags,
        "ready_for_design_review": not blocking_flags,
        "checks": [_compact_reuse_check_record(check) for check in normalized],
        "global_red_lines": list(_GLOBAL_RED_LINES),
        "note": (
            "Mandatory reuse-check plan only. It documents borrow/adapt choices "
            "and does not approve clone, install, vendor, execute, external DB "
            "connections, verdict authority, or trusted status."
        ),
    }


def api_interface_candidate_reuse_check_plan() -> dict[str, Any]:
    """Return the default reuse preflight for API/interface candidate design.

    The sources are already named in the active external asset matrix/registry.
    This function only documents borrow/adapt intent for the next design review;
    it does not read external repos, install tools, launch executors, or grant
    runtime/verdict/trust authority.
    """
    return design_reuse_check_plan([
        {
            "design_topic": "API evidence and denominator vocabulary",
            "source_family": "paper_or_article",
            "source_ref": "RESTestBench mapping row",
            "intake_shape": "knowledge_note",
            "project_artifact": "docs/60_api_candidate API evidence contracts",
            "reuse_decision": (
                "borrow API candidate judging vocabulary while keeping execution owner-gated"
            ),
            "expected_evidence": [
                "API evidence fields remain compact",
                "denominator readiness is not correctness proof",
            ],
            "red_lines": [
                "no API executor from knowledge note",
                "no verdict or trust authority",
            ],
            "boundary": "design vocabulary only; report/projection path stays advisory",
        },
        {
            "design_topic": "API schema or collection executor adapter boundary",
            "source_family": "tool_or_framework",
            "source_ref": "Schemathesis and Newman registry rows",
            "intake_shape": "executor_adapter",
            "project_artifact": "future API candidate executor design",
            "reuse_decision": (
                "reuse runner/evidence-parser concepts later, after owner-approved design"
            ),
            "expected_evidence": [
                "candidate kind is named before runner work",
                "command, parser, isolation, and no-verdict-drift tests are designed first",
            ],
            "red_lines": [
                "no install",
                "no tool invocation",
                "no runtime dependency",
            ],
            "boundary": "future owner-gated adapter only; current path remains report-only",
        },
        {
            "design_topic": "API integration isolation boundary",
            "source_family": "tool_or_framework",
            "source_ref": "WireMock and Testcontainers registry rows",
            "intake_shape": "isolation_support",
            "project_artifact": "future API/integration isolation design",
            "reuse_decision": (
                "reuse isolation concepts only after Asset Gate identifies a concrete need"
            ),
            "expected_evidence": [
                "isolation asset is tied to a candidate kind",
                "network, Docker, and workspace writes are owner-gated",
            ],
            "red_lines": [
                "no Docker path",
                "no service orchestration",
                "no external dependency until design approval",
            ],
            "boundary": "future isolation support only; no live service startup",
        },
        {
            "design_topic": "Named projection and no-drift regression pattern",
            "source_family": "existing_code_pattern",
            "source_ref": "S9/S10 API smoke benchmark and ledger projection tests",
            "intake_shape": "knowledge_note",
            "project_artifact": "future API/interface projection tests",
            "reuse_decision": (
                "reuse named projection plus aggregate/ledger no-drift test pattern"
            ),
            "expected_evidence": [
                "new API views stay separately named",
                "existing aggregate, ledger analytics, signatures, verdict, and trust do not drift",
            ],
            "red_lines": [
                "no generic aggregate key",
                "no existing ledger analytics mutation",
                "no auto-accept",
            ],
            "boundary": "internal test pattern reuse only; no new executor",
        },
    ])


def external_asset_intake_plan(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate and summarize a batch of external asset records.

    This is a design preflight. It returns phase/risk buckets and compact row
    summaries, but it never grants runtime authority or performs any external
    action.
    """
    normalized = [validate_external_asset_record(record) for record in records]
    _reject_duplicate_asset_ids(normalized)

    runtime_risk_records = [
        record["asset_id"]
        for record in normalized
        if record["requires_network"]
        or record["requires_docker"]
        or record["writes_workspace"]
        or record["secrets_or_payload_risk"]
    ]
    future_owner_gated_records = [
        record["asset_id"]
        for record in normalized
        if record["phase_policy"]["current_status"] == "future_owner_gated"
    ]
    metadata_only_records = [
        record["asset_id"]
        for record in normalized
        if record["phase_policy"]["current_status"]
        in {
            "allowed_now_documentation_only",
            "allowed_now_audit_only",
            "allowed_now_tracking_only",
            "design_allowed_metadata_only",
            "reference_allowed_after_readme_audit",
        }
    ]
    rejected_or_deferred_records = [
        record["asset_id"]
        for record in normalized
        if record["phase_policy"]["current_status"] in {"defer", "rejected_as_architecture"}
    ]

    return {
        "plan_version": EXTERNAL_ASSET_INTAKE_PLAN_VERSION,
        "record_schema_version": EXTERNAL_ASSET_RECORD_SCHEMA_VERSION,
        "phase_policy_version": EXTERNAL_ASSET_PHASE_POLICY_VERSION,
        "current_mainline_status": _CURRENT_MAINLINE_STATUS,
        "total_records": len(normalized),
        "by_intake_shape": _counter_dict(record["intake_shape"] for record in normalized),
        "by_current_status": _counter_dict(
            record["phase_policy"]["current_status"] for record in normalized
        ),
        "by_earliest_stage": _counter_dict(
            record["phase_policy"]["earliest_stage"] for record in normalized
        ),
        "metadata_or_reference_only_records": metadata_only_records,
        "future_owner_gated_records": future_owner_gated_records,
        "runtime_risk_records": runtime_risk_records,
        "rejected_or_deferred_records": rejected_or_deferred_records,
        "runtime_actions_allowed_records": [
            record["asset_id"]
            for record in normalized
            if record["runtime_actions_allowed_now"] is True
        ],
        "download_allowed_records": [
            record["asset_id"] for record in normalized if record["download_allowed_now"] is True
        ],
        "install_allowed_records": [
            record["asset_id"] for record in normalized if record["install_allowed_now"] is True
        ],
        "verdict_authority_records": [
            record["asset_id"] for record in normalized if record["verdict_authority"] is True
        ],
        "records": [_compact_plan_record(record) for record in normalized],
        "global_red_lines": list(_GLOBAL_RED_LINES),
        "note": (
            "Design preflight only. A listed record is not approval to download, "
            "install, execute, connect to external databases, vendor code, or "
            "change verdicts."
        ),
    }


def _record_phase_summary(policy: Mapping[str, Any]) -> dict[str, Any]:
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
        "intake_shape": record["intake_shape"],
        "project_artifact": record["project_artifact"],
        "earliest_stage": record["phase_policy"]["earliest_stage"],
        "current_status": record["phase_policy"]["current_status"],
        "next_action": record["next_action"],
        "requires_network": record["requires_network"],
        "requires_docker": record["requires_docker"],
        "writes_workspace": record["writes_workspace"],
        "secrets_or_payload_risk": record["secrets_or_payload_risk"],
        "runtime_actions_allowed_now": record["runtime_actions_allowed_now"],
        "download_allowed_now": record["download_allowed_now"],
        "install_allowed_now": record["install_allowed_now"],
        "verdict_authority": record["verdict_authority"],
    }


def _compact_reuse_check_record(check: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "design_topic": check["design_topic"],
        "source_family": check["source_family"],
        "source_ref": check["source_ref"],
        "intake_shape": check["intake_shape"],
        "project_artifact": check["project_artifact"],
        "reuse_decision": check["reuse_decision"],
        "earliest_stage": check["phase_policy"]["earliest_stage"],
        "current_status": check["phase_policy"]["current_status"],
        "runtime_actions_allowed_now": check["runtime_actions_allowed_now"],
        "download_allowed_now": check["download_allowed_now"],
        "install_allowed_now": check["install_allowed_now"],
        "verdict_authority": check["verdict_authority"],
        "trusted_authority": check["trusted_authority"],
    }


def _reject_duplicate_asset_ids(records: list[Mapping[str, Any]]) -> None:
    counts = Counter(record["asset_id"] for record in records)
    duplicates = sorted(asset_id for asset_id, count in counts.items() if count > 1)
    if duplicates:
        raise ExternalAssetRecordValidationError(
            "external asset records contain duplicate asset_id values: "
            + ", ".join(duplicates)
        )


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values).most_common())


def _reject_unknown_record_fields(record: Mapping[str, Any]) -> None:
    allowed = set(_REQUIRED_RECORD_FIELDS) | set(_OPTIONAL_RECORD_FIELDS)
    unknown = sorted(str(key) for key in record if str(key) not in allowed)
    if unknown:
        raise ExternalAssetRecordValidationError(
            "external asset record has unknown fields: " + ", ".join(unknown)
        )


def _reject_unknown_reuse_fields(check: Mapping[str, Any]) -> None:
    allowed = set(_REQUIRED_REUSE_CHECK_FIELDS) | set(_OPTIONAL_REUSE_CHECK_FIELDS)
    unknown = sorted(str(key) for key in check if str(key) not in allowed)
    if unknown:
        raise DesignReuseCheckValidationError(
            "design reuse check has unknown fields: " + ", ".join(unknown)
        )


def _reject_record_forbidden_fields(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_RECORD_KEYS:
                raise ExternalAssetRecordValidationError(
                    "external asset record must not contain authority, raw payload, "
                    f"or secret field: {child_path}"
                )
            _reject_record_forbidden_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_record_forbidden_fields(child, f"{path}[{index}]")


def _reject_reuse_forbidden_fields(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_REUSE_KEYS:
                raise DesignReuseCheckValidationError(
                    "design reuse check must not contain authority, external "
                    f"action, raw payload, or secret field: {child_path}"
                )
            _reject_reuse_forbidden_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_reuse_forbidden_fields(child, f"{path}[{index}]")


def _record_required_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalAssetRecordValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _record_optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ExternalAssetRecordValidationError(f"{name} must be a string")
    stripped = value.strip()
    return stripped or None


def _record_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ExternalAssetRecordValidationError(f"{name} must be boolean")


def _record_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ExternalAssetRecordValidationError(f"{name} must be a list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ExternalAssetRecordValidationError(
                f"{name}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    if not normalized:
        raise ExternalAssetRecordValidationError(f"{name} must not be empty")
    return normalized


def _reuse_required_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignReuseCheckValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _reuse_optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DesignReuseCheckValidationError(f"{name} must be a string")
    stripped = value.strip()
    return stripped or None


def _reuse_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise DesignReuseCheckValidationError(f"{name} must be a list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise DesignReuseCheckValidationError(
                f"{name}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    if not normalized:
        raise DesignReuseCheckValidationError(f"{name} must not be empty")
    return normalized


def _record_iso_date(value: Any, name: str) -> str:
    text = _record_required_str(value, name)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ExternalAssetRecordValidationError(f"{name} must be ISO-8601 date") from exc
    return text


def _url_looks_secret_bearing(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _SECRET_URL_MARKERS)
