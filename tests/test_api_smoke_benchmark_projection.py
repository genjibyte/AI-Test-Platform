"""S9A API smoke benchmark projection tests."""
from __future__ import annotations

import pytest

from app.benchmark.api_smoke_projection import api_smoke_benchmark_projection
from app.benchmark.models import BenchCaseResult, aggregate


def _case(
    name: str,
    *,
    run_kind: str | None = "external",
    eligible: bool = True,
    reasons: list[str] | None = None,
    requirements: dict | None = None,
    smoke_id: str = "s7c-junit-api-001",
    candidate_kind: str = "junit_api_candidate",
    conclusion: str = "NEED_HUMAN_REVIEW",
    quality_gate_status: str | None = "PASS",
    review_recommendation: str | None = "STRONG_REVIEW_CANDIDATE",
    gen_outcome: str | None = "PASS",
    unit_headline_eligible: bool = False,
    denominator_run_kind: str | None = None,
    redlines: dict | None = None,
) -> BenchCaseResult:
    review_summary = {
        "api_smoke_denominator": {
            "policy_version": "api_smoke_denominator.v1",
            "scope": "separate_api_smoke_denominator",
            "smoke_id": smoke_id,
            "candidate_kind": candidate_kind,
            "run_kind": run_kind if denominator_run_kind is None else denominator_run_kind,
            "eligible_for_api_smoke_denominator": eligible,
            "benchmark_counting_enabled": False,
            "unit_headline_eligible": unit_headline_eligible,
            "not_eligible_reasons": reasons or [],
            "requirements": requirements or {
                "manifest_status_allowed": eligible,
                "candidate_kind_matches": True,
                "target_matches_generation": True,
                "api_evidence_present": eligible,
                "runner_tool_matches": True if eligible else None,
                "redaction_contract_satisfied": True if eligible else None,
                "maven_judge_evidence_present": True,
                "conclusion_needs_review": conclusion == "NEED_HUMAN_REVIEW",
                "trusted_false": True,
            },
        }
    }
    if redlines is not None:
        review_summary["api_smoke_redlines"] = redlines
    return BenchCaseResult(
        name=name,
        repo_url="https://example.test/repo.git",
        target_class="com.example.OwnerApiClient",
        run_kind=run_kind,
        gen_outcome=gen_outcome,
        quality_gate_status=quality_gate_status,
        review_recommendation=review_recommendation,
        conclusion=conclusion,
        review_summary=review_summary,
    )


def _unit_case() -> BenchCaseResult:
    return BenchCaseResult(
        name="ordinary-unit",
        repo_url="https://example.test/repo.git",
        target_class="com.example.Unit",
        run_kind="real",
        conclusion="NEED_HUMAN_REVIEW",
        review_summary={},
    )


def _redlines(
    *,
    flags: list[str] | None = None,
    satisfied: bool | None = True,
) -> dict:
    return {
        "summary_version": "api_smoke_redline_summary.v1",
        "review_flags": flags or [],
        "redlines_satisfied": satisfied,
        "digest_signal": False,
        "verdict_authority": False,
        "trusted_authority": False,
    }


def test_raw_ignores_unit_rows_and_counts_all_api_smoke_source_rows():
    cases = [
        _unit_case(),
        _case("eligible-external", run_kind="external", smoke_id="smoke-a"),
        _case("eligible-real", run_kind="real", smoke_id="smoke-b"),
        _case(
            "ineligible-fake",
            run_kind="fake",
            eligible=False,
            reasons=["api_evidence_absent"],
        ),
        _case(
            "ineligible-external",
            run_kind="external",
            eligible=False,
            reasons=["manifest_status_not_approved_or_active"],
            quality_gate_status="FAIL",
            review_recommendation="REJECT_CANDIDATE",
            gen_outcome="TEST_FAILURE",
        ),
    ]

    summary = api_smoke_benchmark_projection(cases)

    assert summary["view"] == "raw"
    assert summary["run_kind_filter"] is None
    assert summary["total_cases_seen"] == 5
    assert summary["api_smoke_source_rows"] == 4
    assert summary["projected_rows"] == 4
    assert summary["eligible_source_rows"] == 2
    assert summary["ineligible_source_rows"] == 2
    assert summary["by_run_kind"] == {"external": 2, "real": 1, "fake": 1}
    assert summary["by_smoke_id"] == {"s7c-junit-api-001": 2, "smoke-a": 1, "smoke-b": 1}
    assert summary["not_eligible_reason_counts"] == {
        "api_evidence_absent": 1,
        "manifest_status_not_approved_or_active": 1,
    }
    assert summary["gen_outcome_distribution"] == {"PASS": 3, "TEST_FAILURE": 1}
    assert summary["quality_gate_distribution"] == {"PASS": 3, "FAIL": 1}
    assert summary["review_recommendation_distribution"] == {
        "STRONG_REVIEW_CANDIDATE": 3,
        "REJECT_CANDIDATE": 1,
    }


def test_raw_counts_failed_and_null_requirements():
    cases = [
        _case(
            "bad-requirements",
            eligible=False,
            reasons=["api_evidence_absent"],
            requirements={
                "manifest_status_allowed": False,
                "candidate_kind_matches": True,
                "api_evidence_present": False,
                "runner_tool_matches": None,
                "redaction_contract_satisfied": None,
                "trusted_false": True,
            },
        )
    ]

    summary = api_smoke_benchmark_projection(cases)

    assert summary["requirement_failure_counts"] == {
        "manifest_status_allowed": 1,
        "api_evidence_present": 1,
        "runner_tool_matches": 1,
        "redaction_contract_satisfied": 1,
    }


def test_raw_counts_api_smoke_redline_flags_without_aggregate_drift():
    cases = [
        _case("clean", redlines=_redlines()),
        _case(
            "flagged",
            redlines=_redlines(
                flags=[
                    "api_evidence_absent",
                    "redaction_contract_unsatisfied",
                ],
                satisfied=False,
            ),
        ),
        _case(
            "flagged-again",
            redlines=_redlines(flags=["api_evidence_absent"], satisfied=False),
        ),
        _case("redline-summary-absent"),
        _unit_case(),
    ]
    before = aggregate(cases, run_kind="real")

    summary = api_smoke_benchmark_projection(cases)

    assert summary["redline_flag_counts"] == {
        "api_evidence_absent": 2,
        "redaction_contract_unsatisfied": 1,
    }
    assert summary["redlines_satisfied_distribution"] == {
        "false": 2,
        "true": 1,
        "absent": 1,
    }
    assert aggregate(cases, run_kind="real") == before
    assert "api_smoke_redlines" not in aggregate(cases)


def test_headline_includes_only_eligible_real_and_external_rows():
    cases = [
        _case("eligible-external", run_kind="external", smoke_id="external-smoke"),
        _case("eligible-real", run_kind="real", smoke_id="real-smoke"),
        _case("eligible-fake", run_kind="fake"),
        _case("eligible-dryrun", run_kind="dryrun"),
        _case("eligible-smoke", run_kind="smoke"),
        _case("eligible-unknown", run_kind=None),
        _case(
            "ineligible-external",
            run_kind="external",
            eligible=False,
            reasons=["api_evidence_absent"],
        ),
    ]

    summary = api_smoke_benchmark_projection(cases, view="headline")

    assert summary["run_kind_filter"] == ["external", "real"]
    assert summary["api_smoke_source_rows"] == 7
    assert summary["projected_rows"] == 2
    assert summary["eligible_source_rows"] == 6
    assert summary["ineligible_source_rows"] == 1
    assert summary["eligible_projected_rows"] == 2
    assert summary["ineligible_projected_rows"] == 0
    assert summary["by_run_kind"] == {"external": 1, "real": 1}
    assert summary["by_smoke_id"] == {"external-smoke": 1, "real-smoke": 1}
    assert summary["not_eligible_reason_counts"] == {}


def test_headline_counts_redline_flags_only_for_eligible_real_external_rows():
    cases = [
        _case(
            "eligible-external",
            run_kind="external",
            redlines=_redlines(flags=["runner_tool_mismatch"], satisfied=False),
        ),
        _case(
            "eligible-real",
            run_kind="real",
            redlines=_redlines(),
        ),
        _case(
            "eligible-fake",
            run_kind="fake",
            redlines=_redlines(flags=["fake_only"], satisfied=False),
        ),
        _case(
            "ineligible-external",
            run_kind="external",
            eligible=False,
            redlines=_redlines(flags=["ineligible_only"], satisfied=False),
        ),
    ]

    summary = api_smoke_benchmark_projection(cases, view="headline")

    assert summary["projected_rows"] == 2
    assert summary["redline_flag_counts"] == {"runner_tool_mismatch": 1}
    assert summary["redlines_satisfied_distribution"] == {"false": 1, "true": 1}


def test_headline_excludes_top_level_unknown_even_if_denominator_claims_external():
    cases = [
        _case(
            "top-level-unknown",
            run_kind=None,
            denominator_run_kind="external",
        )
    ]

    raw = api_smoke_benchmark_projection(cases)
    headline = api_smoke_benchmark_projection(cases, view="headline")

    assert raw["by_run_kind"] == {"unknown": 1}
    assert raw["eligible_source_rows"] == 1
    assert headline["projected_rows"] == 0
    assert headline["by_run_kind"] == {}


def test_invariant_warnings_surface_without_changing_aggregate_shape():
    cases = [
        _case(
            "bad-invariants",
            unit_headline_eligible=True,
            requirements={
                "manifest_status_allowed": True,
                "candidate_kind_matches": True,
                "target_matches_generation": True,
                "api_evidence_present": True,
                "runner_tool_matches": True,
                "redaction_contract_satisfied": True,
                "maven_judge_evidence_present": True,
                "conclusion_needs_review": True,
                "trusted_false": False,
            },
        ),
        _unit_case(),
    ]
    before = aggregate(cases, run_kind="real")

    summary = api_smoke_benchmark_projection(cases)

    assert summary["trusted_true_cases"] == 1
    assert summary["unit_headline_eligible_cases"] == 1
    assert summary["invariant_warnings"] == [
        "api_smoke_row_marked_unit_headline_eligible",
        "api_smoke_row_not_trusted_false",
    ]
    assert aggregate(cases, run_kind="real") == before
    assert "api_smoke_denominator" not in aggregate(cases)


def test_invalid_projection_view_is_rejected():
    with pytest.raises(ValueError, match="view"):
        api_smoke_benchmark_projection([], view="ledger")
