"""S8 report-only API smoke denominator policy tests."""
from __future__ import annotations

from app.report.generation_report import CONCLUSION, assemble_generation_report


def _bundle(**overrides):
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


def _manifest(**overrides):
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


def _api_report(**bundle_overrides):
    return assemble_generation_report(_bundle(
        candidate_kind="junit_api_candidate",
        api_evidence=_api_evidence(),
        api_smoke_manifest=_manifest(),
        **bundle_overrides,
    ))


def test_unit_report_has_no_api_smoke_denominator():
    report = assemble_generation_report(_bundle())

    assert "api_smoke_denominator" not in report["review_summary"]
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_approved_manifest_with_aligned_evidence_is_denominator_ready_but_not_counted():
    report = _api_report()

    denominator = report["review_summary"]["api_smoke_denominator"]
    manifest = report["review_summary"]["api_smoke_manifest"]
    digest = report["review_summary"]["digest"]

    assert denominator["policy_version"] == "api_smoke_denominator.v1"
    assert denominator["scope"] == "separate_api_smoke_denominator"
    assert denominator["smoke_id"] == "s7c-junit-api-001"
    assert denominator["run_kind"] == "external"
    assert denominator["eligible_for_api_smoke_denominator"] is True
    assert denominator["benchmark_counting_enabled"] is False
    assert denominator["unit_headline_eligible"] is False
    assert denominator["not_eligible_reasons"] == []
    assert denominator["requirements"]["manifest_status_allowed"] is True
    assert denominator["requirements"]["maven_judge_evidence_present"] is True
    assert manifest["alignment"]["denominator_ready"] is True
    assert manifest["alignment"]["not_ready_reasons"] == []
    assert not any(flag["signal"] == "api_smoke_denominator" for flag in digest["flags"])
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_designed_or_retired_manifest_is_not_denominator_ready():
    for status in ("designed", "retired"):
        report = assemble_generation_report(_bundle(
            candidate_kind="junit_api_candidate",
            api_evidence=_api_evidence(),
            api_smoke_manifest=_manifest(status=status),
        ))

        denominator = report["review_summary"]["api_smoke_denominator"]
        assert denominator["eligible_for_api_smoke_denominator"] is False
        assert denominator["requirements"]["manifest_status_allowed"] is False
        assert denominator["not_eligible_reasons"] == [
            "manifest_status_not_approved_or_active"
        ]
        assert report["review_summary"]["api_smoke_manifest"]["alignment"][
            "denominator_ready"
        ] is False


def test_missing_supplied_api_evidence_is_not_denominator_ready():
    report = assemble_generation_report(_bundle(
        candidate_kind="junit_api_candidate",
        api_smoke_manifest=_manifest(),
    ))

    denominator = report["review_summary"]["api_smoke_denominator"]

    assert denominator["eligible_for_api_smoke_denominator"] is False
    assert denominator["requirements"]["api_evidence_present"] is False
    assert denominator["requirements"]["api_evidence_candidate_kind_matches"] is None
    assert denominator["requirements"]["runner_tool_matches"] is None
    assert denominator["not_eligible_reasons"] == ["api_evidence_absent"]
    assert report["review_summary"]["api_smoke_manifest"]["alignment"][
        "denominator_ready"
    ] is False


def test_missing_maven_judge_evidence_is_not_denominator_ready():
    report = _api_report(execution={})

    denominator = report["review_summary"]["api_smoke_denominator"]

    assert denominator["eligible_for_api_smoke_denominator"] is False
    assert denominator["requirements"]["maven_judge_evidence_present"] is False
    assert denominator["not_eligible_reasons"] == ["maven_judge_evidence_absent"]
    assert report["review_summary"]["api_smoke_manifest"]["alignment"][
        "denominator_ready"
    ] is False

