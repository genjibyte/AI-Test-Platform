"""S7A report-only API evidence wiring tests."""
from __future__ import annotations

import pytest

from app.benchmark.models import BenchCaseResult, aggregate
from app.report.api_evidence import ApiEvidenceValidationError
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
        "target": {"target_class": "com.example.OwnerApiClient", "target_method": "ownerName"},
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


def test_default_unit_report_has_no_api_evidence_and_no_top_level_candidate_kind():
    report = assemble_generation_report(_grounded_bundle())

    assert "api_evidence" not in report["review_summary"]
    assert "candidate_kind" not in report
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_explicit_junit_unit_candidate_still_has_no_api_evidence():
    report = assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_unit_candidate",
    ))

    assert "api_evidence" not in report["review_summary"]
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_junit_api_candidate_without_block_attaches_empty_report_only_evidence():
    report = assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_api_candidate",
    ))

    api = report["review_summary"]["api_evidence"]
    assert api["candidate_kind"] == "junit_api_candidate"
    assert api["advisory"] is True
    assert api["report_only"] is True
    assert api["traffic"]["request_count"] == 0
    assert api["execution"]["runner_tool"] == "unknown"
    assert api["conclusion"] == "NEED_HUMAN_REVIEW"
    assert api["trusted"] is False
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_junit_api_candidate_attaches_normalized_api_evidence_without_digest_signal():
    report = assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_api_candidate",
        api_evidence=_api_evidence(),
    ))

    api = report["review_summary"]["api_evidence"]
    digest = report["review_summary"]["digest"]

    assert api["candidate_kind"] == "junit_api_candidate"
    assert api["asset_refs"]["mock_requirement"] == "missing"
    assert api["traffic"]["method_path_summary"] == [{
        "method": "GET",
        "path_template": "/owners/{id}",
        "count": 1,
    }]
    assert api["failures"][0]["code"] == "api_mock_missing"
    assert not any(flag["signal"] == "api_evidence" for flag in digest["flags"])
    assert digest["conclusion"] == "NEED_HUMAN_REVIEW"
    assert report["review_recommendation"] == "STRONG_REVIEW_CANDIDATE"
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_api_evidence_without_generation_candidate_kind_defaults_to_junit_api():
    report = assemble_generation_report(_grounded_bundle(api_evidence=_api_evidence()))

    assert report["review_summary"]["api_evidence"]["candidate_kind"] == (
        "junit_api_candidate"
    )
    assert report["conclusion"] == CONCLUSION
    assert report["trusted"] is False


def test_api_evidence_rejects_authority_or_redaction_unsafe_fields():
    with pytest.raises(ApiEvidenceValidationError, match="authority field"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_evidence=_api_evidence(trusted=True),
        ))

    with pytest.raises(ApiEvidenceValidationError, match="must not persist"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_evidence=_api_evidence(
                redaction={
                    "request_body_persisted": True,
                    "response_body_persisted": False,
                    "secrets_persisted": False,
                }
            ),
        ))


def test_api_evidence_is_rejected_for_unit_candidate_or_mismatched_candidate_kind():
    with pytest.raises(ApiEvidenceValidationError, match="requires candidate_kind"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_unit_candidate",
            api_evidence=_api_evidence(),
        ))

    with pytest.raises(ApiEvidenceValidationError, match="must match"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="junit_api_candidate",
            api_evidence=_api_evidence(candidate_kind="api_schema_candidate"),
        ))


def test_future_api_candidate_kinds_are_not_report_wired_in_s7a():
    with pytest.raises(ApiEvidenceValidationError, match="supports only"):
        assemble_generation_report(_grounded_bundle(
            candidate_kind="api_schema_candidate",
        ))


def test_report_only_api_evidence_does_not_change_benchmark_aggregate_shape():
    cases = [
        BenchCaseResult(
            name="api-smoke",
            repo_url="https://example.test/repo.git",
            target_class="com.example.OwnerApiClient",
            conclusion="NEED_HUMAN_REVIEW",
            run_kind="real",
        )
    ]
    before_keys = set(aggregate(cases).keys())

    assemble_generation_report(_grounded_bundle(
        candidate_kind="junit_api_candidate",
        api_evidence=_api_evidence(),
    ))

    assert set(aggregate(cases).keys()) == before_keys
