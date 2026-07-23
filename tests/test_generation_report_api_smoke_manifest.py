"""S7D1 report-only API smoke manifest carry-through tests."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.report.api_smoke_manifest import ApiSmokeManifestValidationError
from app.report.generation_report import CONCLUSION, assemble_generation_report


def _grounded_bundle(**overrides):
    source = (
        "package com.example;\n"
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.assertEquals;\n\n"
        "class OwnerApiSubmittedTest {\n"
        "  @Test void ownerEndpointReturnsName() {\n"
        "    assertEquals(\"Alice\", new OwnerApiClient().ownerName(42));\n"
        "  }\n"
        "}\n"
    )
    bundle = {
        "target": {
            "target_class": "com.example.OwnerApiClient",
            "target_method": "ownerName",
        },
        "result": {
            "test_class_name": "OwnerApiSubmittedTest",
            "test_source": source,
            "behavior_sources": ["GET /owners/{id} returns owner name"],
            "model": "external-codex",
            "producer_id": "external-codex",
            "trusted": False,
        },
        "write": {
            "file_path": "src/test/java/com/example/OwnerApiSubmittedTest.java",
            "created": True,
            "production_code_touched": False,
            "content": source,
        },
        "execution": {
            "gen_outcome": "PASS",
            "build_outcome": "SUCCESS",
            "gen_total": 1,
            "gen_passed": 1,
            "gen_failed": 0,
            "gen_errors": 0,
            "gen_skipped": 0,
        },
        "coverage_delta": None,
        "run_kind": "external",
        "producer_id": "external-codex",
        "producer_meta": {},
        "error": None,
    }
    bundle.update(overrides)
    return bundle


def _api_evidence(**overrides):
    block = {
        "candidate_kind": "junit_api_candidate",
        "asset_refs": {
            "schema_ref_present": False,
            "collection_ref_present": False,
            "base_url_ref_present": True,
            "auth_requirement": "not_required",
            "fixture_requirement": "present",
            "mock_requirement": "missing",
        },
        "environment": {
            "service_start": "passed",
            "base_url_available": True,
            "network_scope": "local",
        },
        "execution": {
            "runner_tool": "maven_surefire_jacoco",
            "command_summary": "mvn -B test",
            "duration_ms": 500,
            "log_path": "var/jobs/job-api/mvn.log",
        },
        "traffic": {
            "request_count": 1,
            "operation_count": 1,
            "status_summary": [{"class": "2xx", "count": 1}],
            "method_path_summary": [
                {"method": "GET", "path_template": "/owners/{id}", "count": 1}
            ],
        },
        "checks": {
            "schema_failures": 0,
            "assertion_failures": 0,
            "auth_failures": 0,
            "fixture_failures": 0,
            "mock_misses": 1,
            "service_start_failures": 0,
            "runner_errors": 0,
            "timeouts": 0,
        },
        "failures": [{
            "code": "api_mock_missing",
            "severity": "warning",
            "evidence": "notification dependency mock was not declared",
        }],
        "redaction": {
            "request_body_persisted": False,
            "response_body_persisted": False,
            "secrets_persisted": False,
        },
    }
    block.update(overrides)
    return block


def _api_smoke_manifest(**overrides):
    manifest = {
        "schema_version": "api_smoke_manifest.v1",
        "smoke_id": "s7c-junit-api-001",
        "candidate_kind": "junit_api_candidate",
        "status": "approved",
        "target": {
            "target_class": "com.example.OwnerApiClient",
            "target_method": "ownerName",
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


def test_default_unit_report_has_no_api_smoke_manifest():
    report = assemble_generation_report(_grounded_bundle())

    assert "api_smoke_manifest" not in report["review_summary"]
    assert "api_smoke_redlines" not in report["review_summary"]
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_junit_api_candidate_attaches_normalized_api_smoke_manifest():
    report = assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_api_candidate",
        api_evidence=_api_evidence(),
        api_smoke_manifest=_api_smoke_manifest(),
    ))

    manifest = report["review_summary"]["api_smoke_manifest"]
    redlines = report["review_summary"]["api_smoke_redlines"]
    alignment = manifest["alignment"]
    digest = report["review_summary"]["digest"]

    assert manifest["advisory"] is True
    assert manifest["report_only"] is True
    assert manifest["schema_version"] == "api_smoke_manifest.v1"
    assert manifest["smoke_id"] == "s7c-junit-api-001"
    assert manifest["candidate_kind"] == "junit_api_candidate"
    assert manifest["target"]["target_class"] == "com.example.OwnerApiClient"
    assert manifest["asset_requirements"]["fixture_requirement"] == "required"
    assert manifest["execution_policy"] == {
        "runner_tool": "maven_surefire_jacoco",
        "allowed_network_scope": "local",
        "external_network_allowed": False,
        "docker_required": False,
        "real_model_allowed": False,
    }
    assert manifest["evidence_contract"]["report_path"] == (
        "review_summary.api_evidence"
    )
    assert alignment == {
        "target_matches_generation": True,
        "candidate_kind_matches": True,
        "api_evidence_present": True,
        "api_evidence_candidate_kind_matches": True,
        "runner_tool_matches": True,
        "redaction_contract_satisfied": True,
        "denominator_ready": True,
        "not_ready_reasons": [],
    }
    assert redlines["summary_version"] == "api_smoke_redline_summary.v1"
    assert redlines["redlines_satisfied"] is True
    assert redlines["review_flags"] == []
    assert redlines["digest_signal"] is False
    assert redlines["authority_boundary"]["verdict_authority"] is False
    assert redlines["authority_boundary"]["trusted_authority"] is False
    assert not any(flag["signal"] == "api_smoke_manifest" for flag in digest["flags"])
    assert not any(flag["signal"] == "api_smoke_redlines" for flag in digest["flags"])
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_api_smoke_manifest_without_supplied_api_evidence_is_not_denominator_ready():
    report = assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_api_candidate",
        api_smoke_manifest=_api_smoke_manifest(),
    ))

    manifest = report["review_summary"]["api_smoke_manifest"]
    redlines = report["review_summary"]["api_smoke_redlines"]
    alignment = manifest["alignment"]

    assert "api_evidence" in report["review_summary"]
    assert alignment["api_evidence_present"] is False
    assert alignment["api_evidence_candidate_kind_matches"] is None
    assert alignment["runner_tool_matches"] is None
    assert alignment["redaction_contract_satisfied"] is None
    assert alignment["denominator_ready"] is False
    assert alignment["not_ready_reasons"] == ["api_evidence_absent"]
    assert redlines["redlines_satisfied"] is False
    assert redlines["review_flags"] == ["api_evidence_absent"]
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_api_smoke_manifest_requires_explicit_junit_api_candidate():
    with pytest.raises(ApiSmokeManifestValidationError, match="requires"):
        assemble_generation_report(_grounded_bundle(
            api_smoke_manifest=_api_smoke_manifest(),
        ))

    with pytest.raises(ApiSmokeManifestValidationError, match="requires"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_unit_candidate",
            api_smoke_manifest=_api_smoke_manifest(),
        ))


def test_api_smoke_manifest_rejects_target_class_or_method_drift():
    with pytest.raises(ApiSmokeManifestValidationError, match="target_class"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_smoke_manifest=_api_smoke_manifest(
                target={
                    "target_class": "com.example.OtherApiClient",
                    "target_method": "ownerName",
                },
            ),
        ))

    with pytest.raises(ApiSmokeManifestValidationError, match="target_method"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_smoke_manifest=_api_smoke_manifest(
                target={
                    "target_class": "com.example.OwnerApiClient",
                    "target_method": "otherName",
                },
            ),
        ))


def test_api_smoke_manifest_allows_unspecified_manifest_method():
    report = assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_api_candidate",
        api_evidence=_api_evidence(),
        api_smoke_manifest=_api_smoke_manifest(
            target={
                "target_class": "com.example.OwnerApiClient",
                "target_method": None,
            },
        ),
    ))

    assert report["review_summary"]["api_smoke_manifest"]["alignment"][
        "target_matches_generation"
    ] is True


def test_api_smoke_manifest_rejects_api_evidence_runner_drift():
    with pytest.raises(ApiSmokeManifestValidationError, match="runner_tool"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_evidence=_api_evidence(execution={"runner_tool": "schemathesis"}),
            api_smoke_manifest=_api_smoke_manifest(),
        ))


def test_api_smoke_manifest_rejects_authority_or_execution_drift():
    with pytest.raises(ApiSmokeManifestValidationError, match="authority field"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_smoke_manifest=_api_smoke_manifest(trusted=True),
        ))

    with pytest.raises(ApiSmokeManifestValidationError, match="external_network"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_smoke_manifest=_api_smoke_manifest(
                execution_policy={"external_network_allowed": True},
            ),
        ))


def test_api_smoke_manifest_does_not_mutate_input():
    manifest = _api_smoke_manifest()
    before_manifest = deepcopy(manifest)

    assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_api_candidate",
        api_evidence=_api_evidence(),
        api_smoke_manifest=manifest,
    ))

    assert manifest == before_manifest
