"""External asset phase-gate tests."""
from __future__ import annotations

import pytest

from app.governance.external_assets import (
    DESIGN_REUSE_CHECK_PLAN_VERSION,
    DESIGN_REUSE_CHECK_SCHEMA_VERSION,
    EXTERNAL_ASSET_INTAKE_PLAN_VERSION,
    EXTERNAL_ASSET_RECORD_SCHEMA_VERSION,
    EXTERNAL_ASSET_PHASE_POLICY_VERSION,
    KNOWLEDGE_EMBEDDING_DESTINATION_VERSION,
    DesignReuseCheckValidationError,
    ExternalAssetPolicyError,
    ExternalAssetRecordValidationError,
    api_interface_candidate_reuse_check_plan,
    design_reuse_check_plan,
    external_asset_category_policy,
    external_asset_intake_plan,
    external_asset_intake_policy,
    knowledge_embedding_destination,
    validate_design_reuse_check,
    validate_external_asset_record,
)


def _record(**overrides):
    record = {
        "schema_version": EXTERNAL_ASSET_RECORD_SCHEMA_VERSION,
        "asset_id": "defects4j",
        "source_url": "https://github.com/rjust/defects4j",
        "intake_shape": "manifest_seed",
        "project_artifact": "benchmarks/manifest.golden.draft.json",
        "pinned_version_or_commit": "v3.0.1",
        "license_spdx": "MIT",
        "license_verified_at": "2026-07-21",
        "runtime_language": "Java/Perl",
        "requires_network": False,
        "requires_docker": False,
        "writes_workspace": False,
        "secrets_or_payload_risk": False,
        "expected_evidence": [
            "pinned bug id",
            "reproduction command metadata",
        ],
        "red_lines": [
            "no bulk import",
            "no historical benchmark backfill",
        ],
        "next_action": "record metadata only",
    }
    record.update(overrides)
    return record


def _reuse_check(**overrides):
    check = {
        "schema_version": DESIGN_REUSE_CHECK_SCHEMA_VERSION,
        "design_topic": "API smoke projection boundary",
        "source_family": "external_project_registry",
        "source_ref": "Schemathesis and Newman registry rows",
        "intake_shape": "knowledge_note",
        "project_artifact": "docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md",
        "reuse_decision": "borrow evidence vocabulary and keep runner work gated",
        "expected_evidence": [
            "named projection boundary",
            "no-verdict-drift regression test",
        ],
        "red_lines": [
            "no install before owner gate",
            "no API executor from reuse check",
        ],
        "boundary": "report/projection only; no external runtime action",
    }
    check.update(overrides)
    return check


def test_design_reuse_check_normalizes_mandatory_design_metadata():
    normalized = validate_design_reuse_check(_reuse_check())

    assert normalized["schema_version"] == DESIGN_REUSE_CHECK_SCHEMA_VERSION
    assert normalized["mandatory_for_design"] is True
    assert normalized["source_family"] == "external_project_registry"
    assert normalized["intake_shape"] == "knowledge_note"
    assert normalized["phase_policy"]["current_status"] == "allowed_now_documentation_only"
    assert normalized["runtime_actions_allowed_now"] is False
    assert normalized["download_allowed_now"] is False
    assert normalized["install_allowed_now"] is False
    assert normalized["verdict_authority"] is False
    assert normalized["trusted_authority"] is False


def test_design_reuse_check_keeps_future_adapter_reuse_owner_gated():
    normalized = validate_design_reuse_check(_reuse_check(
        design_topic="future API schema executor evidence parser",
        source_family="tool_or_framework",
        source_ref="Schemathesis CLI output contract",
        intake_shape="executor_adapter",
        project_artifact="future api_schema_candidate runner design",
        reuse_decision="defer adapter until owner-approved runner design",
        expected_evidence=["CLI JSON output shape", "parser no-verdict-drift tests"],
        red_lines=["no install", "no service start", "no verdict authority"],
        boundary="design-only adapter notes; no runtime invocation",
    ))

    assert normalized["phase_policy"]["earliest_stage"] == "S13"
    assert normalized["phase_policy"]["current_status"] == "future_owner_gated"
    assert normalized["runtime_actions_allowed_now"] is False
    assert "install" in normalized["phase_policy"]["owner_gate_before"]


@pytest.mark.parametrize(
    "field",
    ["design_topic", "source_ref", "project_artifact", "boundary"],
)
def test_design_reuse_check_requires_non_empty_core_fields(field):
    with pytest.raises(DesignReuseCheckValidationError, match=field):
        validate_design_reuse_check(_reuse_check(**{field: " "}))


def test_design_reuse_check_rejects_unknown_source_family_or_intake_shape():
    with pytest.raises(DesignReuseCheckValidationError, match="unknown source_family"):
        validate_design_reuse_check(_reuse_check(source_family="random_blog_rollup"))

    with pytest.raises(DesignReuseCheckValidationError, match="unknown external asset"):
        validate_design_reuse_check(_reuse_check(intake_shape="runtime_plugin"))


@pytest.mark.parametrize(
    "payload",
    [
        {"install_command": "pip install tool"},
        {"notes": {"token": "do-not-store"}},
        {"expected_evidence": ["safe idea", {"run_command": "pytest external"}]},
    ],
)
def test_design_reuse_check_rejects_runtime_or_secret_authority_fields(payload):
    check = _reuse_check(**payload)

    with pytest.raises(DesignReuseCheckValidationError, match="must not contain"):
        validate_design_reuse_check(check)


def test_design_reuse_check_plan_empty_blocks_design_review():
    plan = design_reuse_check_plan([])

    assert plan["plan_version"] == DESIGN_REUSE_CHECK_PLAN_VERSION
    assert plan["mandatory_for_design"] is True
    assert plan["total_checks"] == 0
    assert plan["blocking_flags"] == ["reuse_check_missing"]
    assert plan["ready_for_design_review"] is False
    assert plan["runtime_actions_allowed_checks"] == []
    assert plan["download_allowed_checks"] == []
    assert plan["install_allowed_checks"] == []
    assert plan["verdict_authority_checks"] == []
    assert plan["trusted_authority_checks"] == []


def test_design_reuse_check_plan_summarizes_mixed_reuse_sources():
    checks = [
        _reuse_check(
            design_topic="API smoke projection boundary",
            source_family="external_project_registry",
            source_ref="Schemathesis and Newman registry rows",
            intake_shape="knowledge_note",
        ),
        _reuse_check(
            design_topic="future API smoke manifest seed",
            source_family="evaluation_set",
            source_ref="Defects4J metadata pattern",
            intake_shape="manifest_seed",
            project_artifact="benchmarks/manifest.golden.draft.json",
            reuse_decision="reuse pinning and license metadata vocabulary",
            expected_evidence=["pinned URL", "license metadata", "no bulk import"],
            red_lines=["no dataset download", "no headline metric"],
            boundary="metadata-only manifest seed",
        ),
        _reuse_check(
            design_topic="future API schema executor evidence parser",
            source_family="tool_or_framework",
            source_ref="Schemathesis CLI output contract",
            intake_shape="executor_adapter",
            project_artifact="future api_schema_candidate runner design",
            reuse_decision="defer parser until owner-approved executor design",
            expected_evidence=["CLI JSON fields", "parser no-verdict-drift tests"],
            red_lines=["no install", "no service start", "no verdict authority"],
            boundary="design-only adapter note",
        ),
    ]

    plan = design_reuse_check_plan(checks)

    assert plan["total_checks"] == 3
    assert plan["blocking_flags"] == []
    assert plan["ready_for_design_review"] is True
    assert plan["by_source_family"] == {
        "external_project_registry": 1,
        "evaluation_set": 1,
        "tool_or_framework": 1,
    }
    assert plan["by_intake_shape"] == {
        "knowledge_note": 1,
        "manifest_seed": 1,
        "executor_adapter": 1,
    }
    assert plan["by_current_status"] == {
        "allowed_now_documentation_only": 1,
        "design_allowed_metadata_only": 1,
        "future_owner_gated": 1,
    }
    assert plan["metadata_only_checks"] == [
        "API smoke projection boundary",
        "future API smoke manifest seed",
    ]
    assert plan["future_owner_gated_checks"] == [
        "future API schema executor evidence parser"
    ]
    assert plan["runtime_actions_allowed_checks"] == []
    assert plan["download_allowed_checks"] == []
    assert plan["install_allowed_checks"] == []
    assert plan["verdict_authority_checks"] == []
    assert plan["trusted_authority_checks"] == []
    assert plan["checks"][2] == {
        "design_topic": "future API schema executor evidence parser",
        "source_family": "tool_or_framework",
        "source_ref": "Schemathesis CLI output contract",
        "intake_shape": "executor_adapter",
        "project_artifact": "future api_schema_candidate runner design",
        "reuse_decision": "defer parser until owner-approved executor design",
        "earliest_stage": "S13",
        "current_status": "future_owner_gated",
        "runtime_actions_allowed_now": False,
        "download_allowed_now": False,
        "install_allowed_now": False,
        "verdict_authority": False,
        "trusted_authority": False,
    }


def test_api_interface_candidate_reuse_plan_is_ready_but_runtime_gated():
    plan = api_interface_candidate_reuse_check_plan()

    assert plan["plan_version"] == DESIGN_REUSE_CHECK_PLAN_VERSION
    assert plan["total_checks"] == 4
    assert plan["blocking_flags"] == []
    assert plan["ready_for_design_review"] is True
    assert plan["by_source_family"] == {
        "paper_or_article": 1,
        "tool_or_framework": 2,
        "existing_code_pattern": 1,
    }
    assert plan["by_intake_shape"] == {
        "knowledge_note": 2,
        "executor_adapter": 1,
        "isolation_support": 1,
    }
    assert plan["by_current_status"] == {
        "allowed_now_documentation_only": 2,
        "future_owner_gated": 2,
    }
    assert plan["metadata_only_checks"] == [
        "API evidence and denominator vocabulary",
        "Named projection and no-drift regression pattern",
    ]
    assert plan["future_owner_gated_checks"] == [
        "API schema or collection executor adapter boundary",
        "API integration isolation boundary",
    ]
    assert plan["runtime_actions_allowed_checks"] == []
    assert plan["download_allowed_checks"] == []
    assert plan["install_allowed_checks"] == []
    assert plan["verdict_authority_checks"] == []
    assert plan["trusted_authority_checks"] == []
    assert {
        record["design_topic"]: record["current_status"]
        for record in plan["checks"]
    } == {
        "API evidence and denominator vocabulary": "allowed_now_documentation_only",
        "API schema or collection executor adapter boundary": "future_owner_gated",
        "API integration isolation boundary": "future_owner_gated",
        "Named projection and no-drift regression pattern": (
            "allowed_now_documentation_only"
        ),
    }


def test_readme_audit_is_allowed_now_but_not_install_or_execution():
    policy = external_asset_intake_policy("readme_audit")

    assert policy["policy_version"] == EXTERNAL_ASSET_PHASE_POLICY_VERSION
    assert policy["current_status"] == "allowed_now_audit_only"
    assert "focused_readme_license_runtime_audit" in policy["allowed_now"]
    assert "install" in policy["owner_gate_before"]
    assert "execute" in policy["owner_gate_before"]
    assert "no_external_execution_without_owner_gate" in policy["global_red_lines"]


def test_manifest_seed_is_metadata_only_before_dataset_slice():
    policy = external_asset_intake_policy("manifest_seed")

    assert policy["earliest_stage"] == "S5B"
    assert policy["current_status"] == "design_allowed_metadata_only"
    assert "pin_url_commit_tag_task_id" in policy["allowed_now"]
    assert "download_data" in policy["owner_gate_before"]
    assert "headline_metric" in policy["owner_gate_before"]


@pytest.mark.parametrize(
    ("shape", "stage"),
    [
        ("dataset_slice", "S11"),
        ("producer_adapter", "S12"),
        ("executor_adapter", "S13"),
        ("isolation_support", "S13"),
    ],
)
def test_runtime_or_data_intake_shapes_are_future_owner_gated(shape, stage):
    policy = external_asset_intake_policy(shape)

    assert policy["earliest_stage"] == stage
    assert policy["current_status"] == "future_owner_gated"
    assert policy["allowed_now"] == ()
    assert policy["owner_gate_before"]


def test_sut_target_can_only_be_audited_reference_now():
    policy = external_asset_intake_policy("sut_target")

    assert policy["earliest_stage"] == "S7C"
    assert policy["current_status"] == "reference_allowed_after_readme_audit"
    assert "reference_in_api_smoke_manifest" in policy["allowed_now"]
    assert "service_orchestration" in policy["owner_gate_before"]
    assert "docker" in policy["owner_gate_before"]


def test_external_database_category_splits_sut_from_platform_storage():
    policy = external_asset_category_policy("external_database")

    assert policy["earliest_stage"] == "S11+ depending on role"
    assert "sut_target" in policy["recommended_intake_shapes"]
    assert "platform storage" in policy["current_answer"]
    assert "database_dump" in policy["not_before"]
    assert "no_external_database_connection_without_owner_gate" in policy["global_red_lines"]


def test_open_source_tool_code_is_adapter_later_not_vendored_now():
    policy = external_asset_category_policy("open_source_tool_code")

    assert policy["earliest_stage"] == "S5B0 for audit, S12/S13 for adapters"
    assert "executor_adapter" in policy["recommended_intake_shapes"]
    assert "vendor_code" in policy["not_before"]
    assert "new_dependency" in policy["not_before"]


def test_policy_returns_defensive_copies():
    policy = external_asset_intake_policy("knowledge_note")
    policy["global_red_lines"].append("mutated")

    again = external_asset_intake_policy("knowledge_note")

    assert "mutated" not in again["global_red_lines"]


def test_unknown_intake_shape_or_category_rejected():
    with pytest.raises(ExternalAssetPolicyError, match="unknown external asset intake_shape"):
        external_asset_intake_policy("external_database")

    with pytest.raises(ExternalAssetPolicyError, match="unknown external asset category"):
        external_asset_category_policy("benchmark")


def test_knowledge_note_destination_routes_to_curated_docs_without_runtime_authority():
    destination = knowledge_embedding_destination("knowledge_note")

    assert destination["destination_version"] == KNOWLEDGE_EMBEDDING_DESTINATION_VERSION
    assert destination["intake_shape"] == "knowledge_note"
    assert "task-routed design doc" in destination["primary_docs"]
    assert (
        "docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md"
        in destination["primary_docs"]
    )
    assert destination["phase_policy"]["current_status"] == "allowed_now_documentation_only"
    assert destination["runtime_actions_allowed_now"] is False
    assert destination["download_allowed_now"] is False
    assert destination["install_allowed_now"] is False
    assert destination["verdict_authority"] is False
    assert destination["trusted_authority"] is False


def test_readme_audit_destination_routes_to_readme_audit_ledger():
    destination = knowledge_embedding_destination("readme_audit")

    assert destination["primary_docs"] == ["docs/knowledge/EXTERNAL_REPO_README_AUDIT.md"]
    assert (
        "docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md"
        in destination["secondary_docs"]
    )
    assert destination["project_artifact"] == "external README audit record"
    assert destination["phase_policy"]["current_status"] == "allowed_now_audit_only"
    assert destination["runtime_actions_allowed_now"] is False


def test_manifest_seed_destination_routes_to_registry_and_golden_set_governance():
    destination = knowledge_embedding_destination("manifest_seed")

    assert "docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md" in (
        destination["primary_docs"]
    )
    assert "docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md" in (
        destination["primary_docs"]
    )
    assert destination["summary_shape"] == "pinned metadata record, not dataset content"
    assert destination["phase_policy"]["current_status"] == "design_allowed_metadata_only"
    assert destination["download_allowed_now"] is False


def test_future_adapter_destination_stays_owner_gated_and_report_boundary_first():
    destination = knowledge_embedding_destination("executor_adapter")

    assert (
        "docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md"
        in destination["primary_docs"]
    )
    assert destination["phase_policy"]["earliest_stage"] == "S13"
    assert destination["phase_policy"]["current_status"] == "future_owner_gated"
    assert destination["project_artifact"] == "future owner-gated executor adapter design"
    assert destination["install_allowed_now"] is False
    assert destination["verdict_authority"] is False


def test_unknown_embedding_destination_is_rejected_by_intake_policy():
    with pytest.raises(ExternalAssetPolicyError, match="unknown external asset intake_shape"):
        knowledge_embedding_destination("runtime_plugin")


def test_external_asset_record_normalizes_manifest_seed_metadata_only():
    normalized = validate_external_asset_record(_record())

    assert normalized["schema_version"] == EXTERNAL_ASSET_RECORD_SCHEMA_VERSION
    assert normalized["asset_id"] == "defects4j"
    assert normalized["intake_shape"] == "manifest_seed"
    assert normalized["phase_policy"]["current_status"] == "design_allowed_metadata_only"
    assert normalized["runtime_actions_allowed_now"] is False
    assert normalized["download_allowed_now"] is False
    assert normalized["install_allowed_now"] is False
    assert normalized["verdict_authority"] is False
    assert "download_data" in normalized["phase_policy"]["owner_gate_before"]


def test_external_asset_record_accepts_future_executor_metadata_without_runtime_permission():
    normalized = validate_external_asset_record(_record(
        asset_id="schemathesis",
        source_url="https://github.com/schemathesis/schemathesis",
        intake_shape="executor_adapter",
        project_artifact="future api_schema_candidate runner design",
        pinned_version_or_commit="not selected",
        license_spdx="MIT",
        runtime_language="Python",
        requires_network=True,
        writes_workspace=True,
        expected_evidence=["CLI JSON output", "schema failure summary"],
        red_lines=["no install before owner gate", "no external network by default"],
        next_action="README audit only",
    ))

    assert normalized["phase_policy"]["earliest_stage"] == "S13"
    assert normalized["phase_policy"]["current_status"] == "future_owner_gated"
    assert normalized["runtime_actions_allowed_now"] is False
    assert "install" in normalized["phase_policy"]["owner_gate_before"]


@pytest.mark.parametrize(
    "field",
    ["asset_id", "source_url", "intake_shape", "project_artifact", "license_spdx"],
)
def test_external_asset_record_requires_non_empty_strings(field):
    record = _record(**{field: " "})

    with pytest.raises(ExternalAssetRecordValidationError, match=field):
        validate_external_asset_record(record)


@pytest.mark.parametrize(
    "field",
    ["requires_network", "requires_docker", "writes_workspace", "secrets_or_payload_risk"],
)
def test_external_asset_record_requires_booleans(field):
    record = _record(**{field: "false"})

    with pytest.raises(ExternalAssetRecordValidationError, match=field):
        validate_external_asset_record(record)


def test_external_asset_record_rejects_unknown_intake_shape():
    record = _record(intake_shape="external_database")

    with pytest.raises(ExternalAssetRecordValidationError, match="unknown external asset"):
        validate_external_asset_record(record)


def test_external_asset_record_rejects_raw_payload_or_secret_fields():
    record = _record(notes={"token": "do-not-store"})

    with pytest.raises(ExternalAssetRecordValidationError, match="secret field: notes.token"):
        validate_external_asset_record(record)


def test_external_asset_record_rejects_secret_bearing_source_url():
    record = _record(source_url="https://example.test/repo?token=secret")

    with pytest.raises(ExternalAssetRecordValidationError, match="source_url"):
        validate_external_asset_record(record)


def test_external_asset_record_rejects_invalid_license_date_and_unknown_fields():
    with pytest.raises(ExternalAssetRecordValidationError, match="license_verified_at"):
        validate_external_asset_record(_record(license_verified_at="2026/07/21"))

    with pytest.raises(ExternalAssetRecordValidationError, match="unknown fields"):
        validate_external_asset_record(_record(runtime_secret="x"))


def test_external_asset_intake_plan_empty_is_safe_preflight():
    plan = external_asset_intake_plan([])

    assert plan["plan_version"] == EXTERNAL_ASSET_INTAKE_PLAN_VERSION
    assert plan["total_records"] == 0
    assert plan["by_intake_shape"] == {}
    assert plan["runtime_actions_allowed_records"] == []
    assert plan["download_allowed_records"] == []
    assert plan["install_allowed_records"] == []
    assert plan["verdict_authority_records"] == []


def test_external_asset_intake_plan_groups_metadata_and_future_gates():
    records = [
        _record(
            asset_id="defects4j",
            intake_shape="manifest_seed",
            project_artifact="benchmarks/manifest.golden.draft.json",
            next_action="metadata only",
        ),
        _record(
            asset_id="schemathesis",
            source_url="https://github.com/schemathesis/schemathesis",
            intake_shape="executor_adapter",
            project_artifact="future api_schema_candidate runner design",
            pinned_version_or_commit="not selected",
            runtime_language="Python",
            requires_network=True,
            writes_workspace=True,
            expected_evidence=["CLI JSON output"],
            red_lines=["no install before owner gate"],
            next_action="README audit only",
        ),
        _record(
            asset_id="spring-petclinic-rest",
            source_url="https://github.com/spring-petclinic/spring-petclinic-rest",
            intake_shape="sut_target",
            project_artifact="api_smoke_manifest target.sut_ref",
            pinned_version_or_commit="not selected",
            license_spdx="Apache-2.0",
            runtime_language="Java",
            expected_evidence=["target URL and commit metadata"],
            red_lines=["no service start before runner design"],
            next_action="audited reference only",
        ),
    ]

    plan = external_asset_intake_plan(records)

    assert plan["total_records"] == 3
    assert plan["by_intake_shape"] == {
        "manifest_seed": 1,
        "executor_adapter": 1,
        "sut_target": 1,
    }
    assert plan["by_current_status"] == {
        "design_allowed_metadata_only": 1,
        "future_owner_gated": 1,
        "reference_allowed_after_readme_audit": 1,
    }
    assert plan["metadata_or_reference_only_records"] == [
        "defects4j",
        "spring-petclinic-rest",
    ]
    assert plan["future_owner_gated_records"] == ["schemathesis"]
    assert plan["runtime_risk_records"] == ["schemathesis"]
    assert plan["runtime_actions_allowed_records"] == []
    assert plan["download_allowed_records"] == []
    assert plan["install_allowed_records"] == []
    assert plan["verdict_authority_records"] == []
    assert plan["records"][1] == {
        "asset_id": "schemathesis",
        "intake_shape": "executor_adapter",
        "project_artifact": "future api_schema_candidate runner design",
        "earliest_stage": "S13",
        "current_status": "future_owner_gated",
        "next_action": "README audit only",
        "requires_network": True,
        "requires_docker": False,
        "writes_workspace": True,
        "secrets_or_payload_risk": False,
        "runtime_actions_allowed_now": False,
        "download_allowed_now": False,
        "install_allowed_now": False,
        "verdict_authority": False,
    }


def test_external_asset_intake_plan_rejects_duplicate_asset_ids():
    records = [
        _record(asset_id="defects4j"),
        _record(asset_id="defects4j", source_url="https://example.test/other"),
    ]

    with pytest.raises(ExternalAssetRecordValidationError, match="duplicate asset_id"):
        external_asset_intake_plan(records)


def test_external_asset_intake_plan_validates_each_record_before_summary():
    records = [
        _record(asset_id="ok"),
        _record(asset_id="bad", source_url="https://example.test/repo?token=secret"),
    ]

    with pytest.raises(ExternalAssetRecordValidationError, match="source_url"):
        external_asset_intake_plan(records)
