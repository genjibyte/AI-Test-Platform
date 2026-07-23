"""API smoke red-line summary tests."""
from __future__ import annotations

from app.report.api_smoke_redlines import (
    REDLINE_SUMMARY_VERSION,
    summarize_api_smoke_redlines,
)


def _api_evidence(**overrides):
    block = {
        "candidate_kind": "junit_api_candidate",
        "execution": {"runner_tool": "maven_surefire_jacoco"},
        "redaction": {
            "request_body_persisted": False,
            "response_body_persisted": False,
            "secrets_persisted": False,
        },
        "conclusion": "NEED_HUMAN_REVIEW",
        "trusted": False,
    }
    block.update(overrides)
    return block


def _manifest(**overrides):
    block = {
        "smoke_id": "s7c-junit-api-001",
        "candidate_kind": "junit_api_candidate",
        "execution_policy": {
            "runner_tool": "maven_surefire_jacoco",
            "external_network_allowed": False,
            "docker_required": False,
            "real_model_allowed": False,
        },
        "alignment": {
            "redaction_contract_satisfied": True,
        },
    }
    block.update(overrides)
    return block


def _denominator(**overrides):
    block = {
        "smoke_id": "s7c-junit-api-001",
        "candidate_kind": "junit_api_candidate",
        "benchmark_counting_enabled": False,
        "unit_headline_eligible": False,
        "not_eligible_reasons": [],
        "requirements": {
            "conclusion_needs_review": True,
            "trusted_false": True,
        },
    }
    block.update(overrides)
    return block


def test_api_smoke_redline_summary_omits_unit_reports():
    assert summarize_api_smoke_redlines({"quality": {}}) is None


def test_api_smoke_redline_summary_marks_clean_smoke_facts_satisfied():
    summary = summarize_api_smoke_redlines({
        "api_evidence": _api_evidence(),
        "api_smoke_manifest": _manifest(),
        "api_smoke_denominator": _denominator(),
    })

    assert summary["summary_version"] == REDLINE_SUMMARY_VERSION
    assert summary["advisory"] is True
    assert summary["report_only"] is True
    assert summary["candidate_kind"] == "junit_api_candidate"
    assert summary["smoke_id"] == "s7c-junit-api-001"
    assert summary["redaction"]["redaction_contract_satisfied"] is True
    assert summary["execution_boundary"]["runner_tool_matches"] is True
    assert summary["execution_boundary"]["external_execution_allowed_now"] is False
    assert summary["authority_boundary"]["conclusion_needs_review"] is True
    assert summary["authority_boundary"]["trusted_false"] is True
    assert summary["authority_boundary"]["benchmark_counting_enabled"] is False
    assert summary["authority_boundary"]["unit_headline_eligible"] is False
    assert summary["review_flags"] == []
    assert summary["redlines_satisfied"] is True
    assert summary["digest_signal"] is False
    assert summary["verdict_authority"] is False
    assert summary["trusted_authority"] is False


def test_api_smoke_redline_summary_surfaces_missing_evidence_once():
    summary = summarize_api_smoke_redlines({
        "api_smoke_manifest": _manifest(alignment={
            "redaction_contract_satisfied": None,
        }),
        "api_smoke_denominator": _denominator(
            not_eligible_reasons=["api_evidence_absent"],
            requirements={
                "conclusion_needs_review": True,
                "trusted_false": True,
            },
        ),
    })

    assert summary["api_evidence_present"] is False
    assert summary["api_smoke_manifest_present"] is True
    assert summary["api_smoke_denominator_present"] is True
    assert summary["review_flags"] == ["api_evidence_absent"]
    assert summary["redlines_satisfied"] is False
    assert summary["redaction"]["redaction_contract_satisfied"] is None


def test_api_smoke_redline_summary_flags_boundary_drift_without_authority():
    summary = summarize_api_smoke_redlines({
        "api_evidence": _api_evidence(
            execution={"runner_tool": "schemathesis"},
            redaction={
                "request_body_persisted": True,
                "response_body_persisted": True,
                "secrets_persisted": True,
            },
            conclusion="AUTO_ACCEPTED",
            trusted=True,
        ),
        "api_smoke_manifest": _manifest(
            execution_policy={
                "runner_tool": "maven_surefire_jacoco",
                "external_network_allowed": True,
                "docker_required": True,
                "real_model_allowed": True,
            },
            alignment={"redaction_contract_satisfied": False},
        ),
        "api_smoke_denominator": _denominator(
            benchmark_counting_enabled=True,
            unit_headline_eligible=True,
            not_eligible_reasons=["runner_tool_mismatch"],
            requirements={
                "conclusion_needs_review": False,
                "trusted_false": False,
            },
        ),
    })

    assert summary["redlines_satisfied"] is False
    assert summary["review_flags"] == [
        "request_body_persisted",
        "response_body_persisted",
        "secrets_persisted",
        "redaction_contract_unsatisfied",
        "runner_tool_mismatch",
        "external_network_allowed",
        "docker_required",
        "real_model_allowed",
        "conclusion_not_need_human_review",
        "trusted_not_false",
        "benchmark_counting_enabled",
        "unit_headline_eligible",
    ]
    assert summary["authority_boundary"]["verdict_authority"] is False
    assert summary["authority_boundary"]["trusted_authority"] is False
