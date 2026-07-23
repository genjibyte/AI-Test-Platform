"""S10D cross-layer API smoke projection boundary tests."""
from __future__ import annotations

from app.benchmark.api_smoke_projection import api_smoke_benchmark_projection
from app.benchmark.models import BenchCaseResult, aggregate
from app.ledger.analytics import aggregate_badcases, badcase_signature, ledger_summary
from app.ledger.api_smoke_projection import api_smoke_ledger_projection
from app.ledger.models import JudgedRecord, Provenance


def _api_smoke_denominator(
    *,
    run_kind: str | None,
    smoke_id: str,
    eligible: bool,
    reasons: list[str] | None = None,
    requirement_failures: list[str] | None = None,
) -> dict:
    failed = set(requirement_failures or [])
    return {
        "policy_version": "api_smoke_denominator.v1",
        "scope": "separate_api_smoke_denominator",
        "smoke_id": smoke_id,
        "candidate_kind": "junit_api_candidate",
        "run_kind": run_kind,
        "eligible_for_api_smoke_denominator": eligible,
        "benchmark_counting_enabled": False,
        "unit_headline_eligible": False,
        "not_eligible_reasons": reasons or [],
        "requirements": {
            "manifest_status_allowed": "manifest_status_allowed" not in failed,
            "candidate_kind_matches": "candidate_kind_matches" not in failed,
            "target_matches_generation": "target_matches_generation" not in failed,
            "api_evidence_present": "api_evidence_present" not in failed,
            "runner_tool_matches": "runner_tool_matches" not in failed,
            "redaction_contract_satisfied": "redaction_contract_satisfied" not in failed,
            "maven_judge_evidence_present": "maven_judge_evidence_present" not in failed,
            "conclusion_needs_review": True,
            "trusted_false": True,
        },
    }


def _api_case(
    name: str,
    *,
    run_kind: str | None,
    smoke_id: str,
    eligible: bool = True,
    reasons: list[str] | None = None,
    requirement_failures: list[str] | None = None,
    gen_outcome: str | None = "PASS",
    quality_gate_status: str | None = "PASS",
    review_recommendation: str | None = "STRONG_REVIEW_CANDIDATE",
) -> BenchCaseResult:
    return BenchCaseResult(
        name=name,
        repo_url="https://example.test/repo.git",
        target_class="com.example.OwnerApiClient",
        target_method="ownerName",
        repo_judged=True,
        run_kind=run_kind,
        gen_outcome=gen_outcome,
        compiled=gen_outcome == "PASS",
        executed=gen_outcome == "PASS",
        passed=gen_outcome == "PASS",
        quality_gate_status=quality_gate_status,
        review_recommendation=review_recommendation,
        conclusion="NEED_HUMAN_REVIEW",
        review_summary={
            "api_smoke_denominator": _api_smoke_denominator(
                run_kind=run_kind,
                smoke_id=smoke_id,
                eligible=eligible,
                reasons=reasons,
                requirement_failures=requirement_failures,
            )
        },
    )


def _unit_case() -> BenchCaseResult:
    return BenchCaseResult(
        name="ordinary-unit",
        repo_url="https://example.test/repo.git",
        target_class="com.example.Unit",
        target_method="value",
        repo_judged=True,
        run_kind="real",
        gen_outcome="PASS",
        compiled=True,
        executed=True,
        passed=True,
        quality_gate_status="PASS",
        review_recommendation="STRONG_REVIEW_CANDIDATE",
        conclusion="NEED_HUMAN_REVIEW",
        review_summary={},
    )


def _api_record(
    record_id: str,
    *,
    run_kind: str | None,
    smoke_id: str,
    eligible: bool = True,
    reasons: list[str] | None = None,
    requirement_failures: list[str] | None = None,
    gen_outcome: str | None = "PASS",
    quality_gate_status: str | None = "PASS",
    review_recommendation: str | None = "STRONG_REVIEW_CANDIDATE",
    failure_type: str | None = None,
) -> JudgedRecord:
    return JudgedRecord(
        record_id=record_id,
        created_at="2026-01-01T00:00:00+00:00",
        repo_url="https://example.test/repo.git",
        target_class="com.example.OwnerApiClient",
        target_method="ownerName",
        provenance=Provenance(author_type="external_agent", author_id="codex"),
        run_kind=run_kind,
        api_smoke_policy_version="api_smoke_denominator.v1",
        api_smoke_scope="separate_api_smoke_denominator",
        api_smoke_smoke_id=smoke_id,
        api_smoke_candidate_kind="junit_api_candidate",
        api_smoke_denominator_eligible=eligible,
        api_smoke_not_eligible_reasons=reasons or [],
        api_smoke_requirement_failures=requirement_failures or [],
        api_smoke_benchmark_counting_enabled=False,
        api_smoke_unit_headline_eligible=False,
        gen_outcome=gen_outcome,
        compiled=gen_outcome == "PASS",
        executed=gen_outcome == "PASS",
        passed=gen_outcome == "PASS",
        quality_gate_status=quality_gate_status,
        review_recommendation=review_recommendation,
        conclusion="NEED_HUMAN_REVIEW",
        failure_type=failure_type,
    )


def _unit_record() -> JudgedRecord:
    return JudgedRecord(
        record_id="unit-1",
        created_at="2026-01-01T00:00:00+00:00",
        repo_url="https://example.test/repo.git",
        target_class="com.example.Unit",
        target_method="value",
        provenance=Provenance(author_type="platform_generator", author_id="builtin"),
        run_kind="real",
        gen_outcome="PASS",
        compiled=True,
        executed=True,
        passed=True,
        quality_gate_status="PASS",
        review_recommendation="STRONG_REVIEW_CANDIDATE",
        conclusion="NEED_HUMAN_REVIEW",
    )


def test_api_smoke_projection_views_are_named_and_do_not_mutate_existing_views():
    cases = [
        _unit_case(),
        _api_case("api-external", run_kind="external", smoke_id="smoke-external"),
        _api_case("api-real", run_kind="real", smoke_id="smoke-real"),
        _api_case(
            "api-fake-ineligible",
            run_kind="fake",
            smoke_id="smoke-fake",
            eligible=False,
            reasons=["api_evidence_absent"],
            requirement_failures=["api_evidence_present"],
            gen_outcome="TEST_FAILURE",
            quality_gate_status="FAIL",
            review_recommendation="REJECT_CANDIDATE",
        ),
    ]
    records = [
        _unit_record(),
        _api_record("api-1", run_kind="external", smoke_id="smoke-external"),
        _api_record("api-2", run_kind="real", smoke_id="smoke-real"),
        _api_record(
            "api-3",
            run_kind="fake",
            smoke_id="smoke-fake",
            eligible=False,
            reasons=["api_evidence_absent"],
            requirement_failures=["api_evidence_present"],
            gen_outcome="TEST_FAILURE",
            quality_gate_status="FAIL",
            review_recommendation="REJECT_CANDIDATE",
            failure_type="TEST_FAILURE",
        ),
    ]
    aggregate_before = aggregate(cases)
    aggregate_real_before = aggregate(cases, run_kind="real")
    ledger_before = ledger_summary(records)
    ledger_real_before = ledger_summary(records, run_kind="real")
    badcases_before = [stat.model_dump() for stat in aggregate_badcases(records)]
    signature_before = badcase_signature(records[-1])

    benchmark_raw = api_smoke_benchmark_projection(cases)
    benchmark_headline = api_smoke_benchmark_projection(cases, view="headline")
    ledger_raw = api_smoke_ledger_projection(records)
    ledger_headline = api_smoke_ledger_projection(records, view="headline")

    assert benchmark_raw["projection_version"] == "api_smoke_benchmark_projection.v1"
    assert ledger_raw["projection_version"] == "api_smoke_ledger_projection.v1"
    assert benchmark_raw["projection_version"] != ledger_raw["projection_version"]

    assert benchmark_raw["api_smoke_source_rows"] == 3
    assert benchmark_raw["eligible_source_rows"] == 2
    assert benchmark_raw["ineligible_source_rows"] == 1
    assert benchmark_headline["projected_rows"] == 2
    assert benchmark_headline["by_run_kind"] == {"external": 1, "real": 1}
    assert benchmark_headline["not_eligible_reason_counts"] == {}
    assert benchmark_headline["unit_headline_eligible_cases"] == 0
    assert benchmark_headline["trusted_true_cases"] == 0

    assert ledger_raw["api_smoke_source_records"] == 3
    assert ledger_raw["eligible_source_records"] == 2
    assert ledger_raw["ineligible_source_records"] == 1
    assert ledger_headline["projected_records"] == 2
    assert ledger_headline["by_run_kind"] == {"external": 1, "real": 1}
    assert ledger_headline["not_eligible_reason_counts"] == {}
    assert ledger_headline["benchmark_counting_enabled_records"] == 0
    assert ledger_headline["unit_headline_eligible_records"] == 0
    assert ledger_headline["need_human_review_records"] == 2

    assert aggregate(cases) == aggregate_before
    assert aggregate(cases, run_kind="real") == aggregate_real_before
    assert ledger_summary(records) == ledger_before
    assert ledger_summary(records, run_kind="real") == ledger_real_before
    assert [stat.model_dump() for stat in aggregate_badcases(records)] == badcases_before
    assert badcase_signature(records[-1]) == signature_before
    assert signature_before == "TEST_FAILURE@com.example.OwnerApiClient#ownerName"
