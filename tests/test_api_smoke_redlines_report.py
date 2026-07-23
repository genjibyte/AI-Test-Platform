"""API smoke red-line Markdown presentation tests."""
from __future__ import annotations

from app.report import render_api_smoke_redlines_markdown
from app.report.api_smoke_redlines import summarize_api_smoke_redlines


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
        "smoke_id": "smoke|pipe",
        "candidate_kind": "junit_api_candidate",
        "execution_policy": {
            "runner_tool": "maven_surefire_jacoco",
            "external_network_allowed": False,
            "docker_required": False,
            "real_model_allowed": False,
        },
        "alignment": {"redaction_contract_satisfied": True},
    }
    block.update(overrides)
    return block


def _denominator(**overrides):
    block = {
        "smoke_id": "smoke|pipe",
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


def test_render_api_smoke_redlines_markdown_omits_absent_summary():
    assert render_api_smoke_redlines_markdown({}) == ""
    assert render_api_smoke_redlines_markdown({"api_evidence": _api_evidence()}) == ""


def test_render_api_smoke_redlines_markdown_is_presentation_only():
    review_summary = {
        "api_evidence": _api_evidence(),
        "api_smoke_manifest": _manifest(),
        "api_smoke_denominator": _denominator(),
    }
    review_summary["api_smoke_redlines"] = summarize_api_smoke_redlines(review_summary)

    md = render_api_smoke_redlines_markdown(review_summary)

    assert "## API smoke red lines - REPORT ONLY" in md
    assert "candidate_kind: junit_api_candidate" in md
    assert "smoke_id: smoke/pipe" in md
    assert "redlines_satisfied: True" in md
    assert "digest_signal: False" in md
    assert "verdict_authority=False" in md
    assert "trusted_authority=False" in md
    assert "external_execution_allowed_now=False" in md
    assert "benchmark_counting_enabled=False" in md
    assert "|" in md


def test_render_api_smoke_redlines_markdown_surfaces_flags():
    review_summary = {
        "api_smoke_manifest": _manifest(
            alignment={"redaction_contract_satisfied": None},
        ),
        "api_smoke_denominator": _denominator(
            not_eligible_reasons=["api_evidence_absent"],
        ),
    }
    review_summary["api_smoke_redlines"] = summarize_api_smoke_redlines(review_summary)

    md = render_api_smoke_redlines_markdown(review_summary)

    assert "redlines_satisfied: False" in md
    assert "review_flags: api_evidence_absent" in md
    assert "evidence_present: False" in md
