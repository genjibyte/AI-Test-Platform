"""Compact API evidence block tests (docs/60_api_candidate/04)."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.benchmark.models import BenchCaseResult, aggregate
from app.report.api_evidence import (
    ApiEvidenceValidationError,
    SCHEMA_VERSION,
    empty_api_evidence,
    validate_api_evidence_block,
)


def _valid_block(**overrides):
    block = {
        "schema_version": SCHEMA_VERSION,
        "advisory": True,
        "report_only": True,
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
            "duration_ms": 1200,
            "log_path": "var/jobs/job-1/mvn.log",
        },
        "traffic": {
            "request_count": 3,
            "operation_count": 2,
            "status_summary": [
                {"class": "2xx", "count": 2},
                {"class": "5xx", "count": 1},
            ],
            "method_path_summary": [
                {"method": "get", "path_template": "/owners/{id}", "count": 2},
                {"method": "POST", "path_template": "/owners", "count": 1},
            ],
        },
        "checks": {
            "schema_failures": 0,
            "assertion_failures": 1,
            "auth_failures": 0,
            "fixture_failures": 0,
            "mock_misses": 1,
            "service_start_failures": 0,
            "runner_errors": 0,
            "timeouts": 0,
        },
        "failures": [
            {
                "code": "api_assertion_failure",
                "severity": "blocker",
                "evidence": "GET /owners/{id} returned an unexpected owner name",
            },
            {
                "code": "api_mock_missing",
                "severity": "warning",
                "evidence": "external notification dependency not mocked",
            },
        ],
        "redaction": {
            "request_body_persisted": False,
            "response_body_persisted": False,
            "secrets_persisted": False,
        },
    }
    block.update(overrides)
    return block


def test_valid_api_evidence_block_normalizes_without_mutating_input():
    block = _valid_block()
    before = deepcopy(block)

    evidence = validate_api_evidence_block(block)

    assert block == before
    assert evidence["schema_version"] == SCHEMA_VERSION
    assert evidence["candidate_kind"] == "junit_api_candidate"
    assert evidence["advisory"] is True
    assert evidence["report_only"] is True
    assert evidence["asset_refs"]["mock_requirement"] == "missing"
    assert evidence["traffic"]["method_path_summary"][0] == {
        "method": "GET",
        "path_template": "/owners/{id}",
        "count": 2,
    }
    assert evidence["checks"]["assertion_failures"] == 1
    assert evidence["failures"][0]["code"] == "api_assertion_failure"
    assert evidence["redaction"] == {
        "request_body_persisted": False,
        "response_body_persisted": False,
        "secrets_persisted": False,
    }
    assert evidence["conclusion"] == "NEED_HUMAN_REVIEW"
    assert evidence["trusted"] is False


def test_empty_api_evidence_defaults_to_sparse_report_only_junit_api_block():
    evidence = empty_api_evidence()

    assert evidence["candidate_kind"] == "junit_api_candidate"
    assert evidence["asset_refs"]["base_url_ref_present"] is None
    assert evidence["asset_refs"]["fixture_requirement"] == "unknown"
    assert evidence["environment"]["network_scope"] == "unknown"
    assert evidence["execution"]["runner_tool"] == "unknown"
    assert evidence["traffic"]["request_count"] == 0
    assert evidence["checks"]["runner_errors"] == 0
    assert evidence["failures"] == []
    assert evidence["advisory"] is True
    assert evidence["report_only"] is True


@pytest.mark.parametrize("field", ["trusted", "conclusion", "auto_accept"])
def test_api_evidence_rejects_authority_fields(field):
    with pytest.raises(ApiEvidenceValidationError, match="authority field"):
        validate_api_evidence_block(_valid_block(**{field: True}))


def test_api_evidence_rejects_nested_authority_fields():
    block = _valid_block(failures=[
        {
            "code": "api_runner_error",
            "severity": "blocker",
            "evidence": "runner failed",
            "trusted": True,
        }
    ])

    with pytest.raises(ApiEvidenceValidationError, match="failures\\[0\\].trusted"):
        validate_api_evidence_block(block)


@pytest.mark.parametrize(
    "redaction",
    [
        {"request_body_persisted": True},
        {"response_body_persisted": True},
        {"secrets_persisted": True},
    ],
)
def test_api_evidence_rejects_redaction_violations(redaction):
    with pytest.raises(ApiEvidenceValidationError, match="must not persist"):
        validate_api_evidence_block(_valid_block(redaction=redaction))


@pytest.mark.parametrize("field", ["request_body", "response_body", "authorization", "token"])
def test_api_evidence_rejects_raw_payload_or_secret_like_fields(field):
    block = _valid_block(traffic={field: "do-not-store-me"})

    with pytest.raises(ApiEvidenceValidationError, match="raw payload/secret field"):
        validate_api_evidence_block(block)


def test_missing_assets_are_evidence_not_verdicts():
    evidence = validate_api_evidence_block(_valid_block(
        asset_refs={
            "schema_ref_present": None,
            "collection_ref_present": None,
            "base_url_ref_present": False,
            "auth_requirement": "missing",
            "fixture_requirement": "missing",
            "mock_requirement": "missing",
        },
        failures=[
            {
                "code": "api_asset_missing_base_url",
                "severity": "blocker",
                "evidence": "base URL ref was not declared",
            }
        ],
    ))

    assert evidence["asset_refs"]["base_url_ref_present"] is False
    assert evidence["asset_refs"]["auth_requirement"] == "missing"
    assert evidence["failures"][0]["code"] == "api_asset_missing_base_url"
    assert evidence["conclusion"] == "NEED_HUMAN_REVIEW"
    assert evidence["trusted"] is False


def test_api_evidence_rejects_invalid_counts_and_statuses():
    with pytest.raises(ApiEvidenceValidationError, match="traffic.request_count"):
        validate_api_evidence_block(_valid_block(
            traffic={"request_count": -1},
        ))

    with pytest.raises(ApiEvidenceValidationError, match="environment.network_scope"):
        validate_api_evidence_block(_valid_block(
            environment={"network_scope": "internet"},
        ))


def test_api_evidence_does_not_change_benchmark_aggregate_shape():
    cases = [
        BenchCaseResult(
            name="api-smoke",
            repo_url="https://example.test/repo.git",
            target_class="com.example.OwnerApi",
            conclusion="NEED_HUMAN_REVIEW",
            run_kind="real",
        )
    ]
    before_keys = set(aggregate(cases).keys())

    validate_api_evidence_block(_valid_block())

    assert set(aggregate(cases).keys()) == before_keys
