"""JUnit API smoke manifest tests (docs/60_api_candidate/07)."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.report.api_smoke_manifest import (
    RUNNER_TOOL,
    SCHEMA_VERSION,
    ApiSmokeManifestValidationError,
    validate_api_smoke_manifest,
)


def _minimal_manifest(**overrides):
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "smoke_id": "s7c-junit-api-001",
        "candidate_kind": "junit_api_candidate",
        "status": "approved",
        "target": {
            "target_class": "com.example.OwnerController",
            "target_method": None,
            "api_style": "mockmvc",
            "sut_ref": {
                "intake_shape": "none",
                "name": "project-under-judge",
            },
        },
        "asset_requirements": {
            "service_start_requirement": "not_required",
            "base_url_requirement": "not_required",
            "auth_requirement": "not_required",
            "fixture_requirement": "required",
            "mock_requirement": "unknown",
            "business_oracle_ref_requirement": "present",
        },
    }
    manifest.update(overrides)
    return manifest


def test_valid_api_smoke_manifest_normalizes_without_mutating_input():
    manifest = _minimal_manifest()
    before = deepcopy(manifest)

    normalized = validate_api_smoke_manifest(manifest)

    assert manifest == before
    assert normalized["schema_version"] == SCHEMA_VERSION
    assert normalized["smoke_id"] == "s7c-junit-api-001"
    assert normalized["candidate_kind"] == "junit_api_candidate"
    assert normalized["target"]["api_style"] == "mockmvc"
    assert normalized["target"]["sut_ref"]["intake_shape"] == "none"
    assert normalized["submission_contract"]["required_fields"] == [
        "target_class",
        "test_source",
        "producer_id",
        "candidate_kind",
    ]
    assert normalized["submission_contract"]["fixed_values"] == {
        "candidate_kind": "junit_api_candidate",
    }
    assert normalized["asset_requirements"]["fixture_requirement"] == "required"
    assert normalized["execution_policy"] == {
        "runner_tool": RUNNER_TOOL,
        "allowed_network_scope": "local",
        "external_network_allowed": False,
        "docker_required": False,
        "real_model_allowed": False,
        "timeout_policy_ref": "current judge timeout",
    }
    assert normalized["evidence_contract"]["report_path"] == (
        "review_summary.api_evidence"
    )
    assert normalized["evidence_contract"]["minimum_api_evidence"][
        "candidate_kind"
    ] == "junit_api_candidate"


def test_sparse_manifest_defaults_to_no_external_execution_or_docker():
    normalized = validate_api_smoke_manifest({
        "smoke_id": "s7c-junit-api-002",
        "target": {"target_class": "com.example.OwnerController"},
    })

    assert normalized["status"] == "designed"
    assert normalized["target"]["api_style"] == "unknown"
    assert normalized["target"]["sut_ref"] == {
        "intake_shape": "none",
        "name": "project-under-judge",
        "url": None,
        "commit": None,
        "readme_audit_ref": None,
        "license_note": None,
    }
    assert normalized["asset_requirements"]["service_start_requirement"] == "unknown"
    assert normalized["execution_policy"]["runner_tool"] == RUNNER_TOOL
    assert normalized["execution_policy"]["allowed_network_scope"] == "local"
    assert normalized["execution_policy"]["external_network_allowed"] is False
    assert normalized["execution_policy"]["docker_required"] is False
    assert normalized["execution_policy"]["real_model_allowed"] is False


def test_api_smoke_manifest_rejects_unsupported_candidate_kind():
    manifest = _minimal_manifest(candidate_kind="api_schema_candidate")

    with pytest.raises(ApiSmokeManifestValidationError, match="supports only"):
        validate_api_smoke_manifest(manifest)


def test_api_smoke_manifest_rejects_non_maven_runner():
    manifest = _minimal_manifest(execution_policy={"runner_tool": "schemathesis"})

    with pytest.raises(ApiSmokeManifestValidationError, match="runner_tool"):
        validate_api_smoke_manifest(manifest)


@pytest.mark.parametrize(
    "execution_policy",
    [
        {"external_network_allowed": True},
        {"docker_required": True},
        {"real_model_allowed": True},
    ],
)
def test_api_smoke_manifest_rejects_execution_drift(execution_policy):
    manifest = _minimal_manifest(execution_policy=execution_policy)

    with pytest.raises(ApiSmokeManifestValidationError):
        validate_api_smoke_manifest(manifest)


@pytest.mark.parametrize("field", ["trusted", "conclusion", "auto_accept"])
def test_api_smoke_manifest_rejects_authority_fields(field):
    manifest = _minimal_manifest(**{field: True})

    with pytest.raises(ApiSmokeManifestValidationError, match="authority field"):
        validate_api_smoke_manifest(manifest)


def test_api_smoke_manifest_rejects_nested_authority_fields():
    manifest = _minimal_manifest(
        target={
            "target_class": "com.example.OwnerController",
            "sut_ref": {
                "intake_shape": "none",
                "trusted": True,
            },
        },
    )

    with pytest.raises(ApiSmokeManifestValidationError, match="target.sut_ref.trusted"):
        validate_api_smoke_manifest(manifest)


@pytest.mark.parametrize(
    "field",
    ["request_body", "response_body", "token", ".env", "service_snapshot"],
)
def test_api_smoke_manifest_rejects_raw_payload_or_secret_like_fields(field):
    manifest = _minimal_manifest(target={"target_class": "x", field: "do-not-store"})

    with pytest.raises(ApiSmokeManifestValidationError, match="raw payload/secret"):
        validate_api_smoke_manifest(manifest)


def test_api_smoke_manifest_rejects_unaudited_external_sut_target():
    manifest = _minimal_manifest(
        target={
            "target_class": "com.example.OwnerController",
            "sut_ref": {
                "intake_shape": "sut_target",
                "name": "Spring PetClinic REST",
                "url": "https://github.com/spring-petclinic/spring-petclinic-rest",
            },
        },
    )

    with pytest.raises(ApiSmokeManifestValidationError, match="readme_audit_ref"):
        validate_api_smoke_manifest(manifest)


def test_api_smoke_manifest_accepts_audited_external_sut_target_as_reference_only():
    normalized = validate_api_smoke_manifest(_minimal_manifest(
        target={
            "target_class": "com.example.OwnerController",
            "api_style": "restassured_local",
            "sut_ref": {
                "intake_shape": "sut_target",
                "name": "Spring PetClinic REST",
                "url": "https://github.com/spring-petclinic/spring-petclinic-rest",
                "commit": "abc123",
                "readme_audit_ref": "docs/knowledge/EXTERNAL_REPO_README_AUDIT.md#spring-petclinic-rest",
                "license_note": "see audit",
            },
        },
    ))

    assert normalized["target"]["sut_ref"]["intake_shape"] == "sut_target"
    assert normalized["target"]["sut_ref"]["readme_audit_ref"].endswith(
        "#spring-petclinic-rest"
    )
    assert normalized["execution_policy"]["runner_tool"] == RUNNER_TOOL
    assert normalized["execution_policy"]["docker_required"] is False


def test_api_smoke_manifest_rejects_contract_downgrade():
    manifest = _minimal_manifest(submission_contract={
        "required_fields": ["target_class", "test_source"],
        "fixed_values": {"candidate_kind": "junit_api_candidate"},
    })

    with pytest.raises(ApiSmokeManifestValidationError, match="producer_id"):
        validate_api_smoke_manifest(manifest)


def test_api_smoke_manifest_rejects_evidence_contract_drift():
    manifest = _minimal_manifest(evidence_contract={
        "report_path": "top_level.api_evidence",
    })

    with pytest.raises(ApiSmokeManifestValidationError, match="report_path"):
        validate_api_smoke_manifest(manifest)

