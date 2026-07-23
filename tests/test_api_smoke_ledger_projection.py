"""S10B API smoke ledger projection tests."""
from __future__ import annotations

import pytest

from app.ledger.analytics import aggregate_badcases, badcase_signature, ledger_summary
from app.ledger.api_smoke_projection import api_smoke_ledger_projection
from app.ledger.api_smoke_report import render_api_smoke_ledger_markdown
from app.ledger.models import JudgedRecord, Provenance


def _rec(
    record_id: str,
    *,
    run_kind: str | None = "external",
    eligible: bool = True,
    reasons: list[str] | None = None,
    requirement_failures: list[str] | None = None,
    smoke_id: str | None = "s7c-junit-api-001",
    candidate_kind: str | None = "junit_api_candidate",
    policy_version: str | None = "api_smoke_denominator.v1",
    scope: str | None = "separate_api_smoke_denominator",
    gen_outcome: str | None = "PASS",
    quality_gate_status: str | None = "PASS",
    review_recommendation: str | None = "STRONG_REVIEW_CANDIDATE",
    conclusion: str | None = "NEED_HUMAN_REVIEW",
    failure_type: str | None = None,
    benchmark_counting_enabled: bool | None = False,
    unit_headline_eligible: bool | None = False,
) -> JudgedRecord:
    return JudgedRecord(
        record_id=record_id,
        created_at=f"2026-01-01T00:00:{record_id[-1]}+00:00",
        repo_url="https://example.test/repo.git",
        target_class="com.example.OwnerApiClient",
        target_method="ownerName",
        provenance=Provenance(author_type="external_agent", author_id="codex"),
        run_kind=run_kind,
        api_smoke_policy_version=policy_version,
        api_smoke_scope=scope,
        api_smoke_smoke_id=smoke_id,
        api_smoke_candidate_kind=candidate_kind,
        api_smoke_denominator_eligible=eligible,
        api_smoke_not_eligible_reasons=reasons or [],
        api_smoke_requirement_failures=requirement_failures or [],
        api_smoke_benchmark_counting_enabled=benchmark_counting_enabled,
        api_smoke_unit_headline_eligible=unit_headline_eligible,
        gen_outcome=gen_outcome,
        quality_gate_status=quality_gate_status,
        review_recommendation=review_recommendation,
        conclusion=conclusion,
        failure_type=failure_type,
    )


def _unit_rec() -> JudgedRecord:
    return JudgedRecord(
        record_id="unit",
        repo_url="https://example.test/repo.git",
        target_class="com.example.Unit",
        provenance=Provenance(author_type="platform_generator", author_id="deepseek"),
        run_kind="real",
        conclusion="NEED_HUMAN_REVIEW",
    )


def test_raw_ignores_unit_rows_and_counts_all_api_smoke_source_records():
    records = [
        _unit_rec(),
        _rec("api1", run_kind="external", smoke_id="smoke-a"),
        _rec("api2", run_kind="real", smoke_id="smoke-b"),
        _rec(
            "api3",
            run_kind="fake",
            eligible=False,
            reasons=["api_evidence_absent"],
            requirement_failures=["api_evidence_present", "runner_tool_matches"],
        ),
        _rec(
            "api4",
            run_kind="external",
            eligible=False,
            reasons=["manifest_status_not_approved_or_active"],
            requirement_failures=["manifest_status_allowed"],
            gen_outcome="TEST_FAILURE",
            quality_gate_status="FAIL",
            review_recommendation="REJECT_CANDIDATE",
        ),
    ]

    summary = api_smoke_ledger_projection(records)

    assert summary["view"] == "raw"
    assert summary["run_kind_filter"] is None
    assert summary["total_records_seen"] == 5
    assert summary["api_smoke_source_records"] == 4
    assert summary["projected_records"] == 4
    assert summary["eligible_source_records"] == 2
    assert summary["ineligible_source_records"] == 2
    assert summary["by_run_kind"] == {"external": 2, "real": 1, "fake": 1}
    assert summary["by_smoke_id"] == {"s7c-junit-api-001": 2, "smoke-a": 1, "smoke-b": 1}
    assert summary["not_eligible_reason_counts"] == {
        "api_evidence_absent": 1,
        "manifest_status_not_approved_or_active": 1,
    }
    assert summary["requirement_failure_counts"] == {
        "api_evidence_present": 1,
        "runner_tool_matches": 1,
        "manifest_status_allowed": 1,
    }
    assert summary["gen_outcome_distribution"] == {"PASS": 3, "TEST_FAILURE": 1}
    assert summary["quality_gate_distribution"] == {"PASS": 3, "FAIL": 1}
    assert summary["review_recommendation_distribution"] == {
        "STRONG_REVIEW_CANDIDATE": 3,
        "REJECT_CANDIDATE": 1,
    }


def test_headline_includes_only_eligible_real_and_external_source_records():
    records = [
        _rec("api1", run_kind="external", smoke_id="external-smoke"),
        _rec("api2", run_kind="real", smoke_id="real-smoke"),
        _rec("api3", run_kind="fake"),
        _rec("api4", run_kind="dryrun"),
        _rec("api5", run_kind="smoke"),
        _rec("api6", run_kind=None),
        _rec(
            "api7",
            run_kind="external",
            eligible=False,
            reasons=["api_evidence_absent"],
        ),
    ]

    summary = api_smoke_ledger_projection(records, view="headline")

    assert summary["run_kind_filter"] == ["external", "real"]
    assert summary["api_smoke_source_records"] == 7
    assert summary["projected_records"] == 2
    assert summary["eligible_source_records"] == 6
    assert summary["ineligible_source_records"] == 1
    assert summary["eligible_projected_records"] == 2
    assert summary["ineligible_projected_records"] == 0
    assert summary["by_run_kind"] == {"external": 1, "real": 1}
    assert summary["by_smoke_id"] == {"external-smoke": 1, "real-smoke": 1}
    assert summary["not_eligible_reason_counts"] == {}


def test_wrong_policy_or_scope_is_not_a_source_record():
    records = [
        _rec("api1", policy_version="api_smoke_denominator.v2"),
        _rec("api2", scope="unit_headline"),
        _rec("api3"),
    ]

    summary = api_smoke_ledger_projection(records)

    assert summary["total_records_seen"] == 3
    assert summary["api_smoke_source_records"] == 1
    assert summary["projected_records"] == 1
    assert summary["by_run_kind"] == {"external": 1}


def test_projection_does_not_change_existing_ledger_analytics_or_badcase_signature():
    records = [
        _rec("api1", run_kind="external", failure_type="TEST_FAILURE"),
        _rec("api2", run_kind="real"),
        _unit_rec(),
    ]
    before_summary = ledger_summary(records)
    before_badcases = [stat.model_dump() for stat in aggregate_badcases(records)]

    projection = api_smoke_ledger_projection(records)

    assert projection["api_smoke_source_records"] == 2
    assert ledger_summary(records) == before_summary
    assert [stat.model_dump() for stat in aggregate_badcases(records)] == before_badcases
    assert badcase_signature(records[0]) == "TEST_FAILURE@com.example.OwnerApiClient#ownerName"


def test_invariant_warnings_are_descriptive_only():
    records = [
        _rec(
            "api1",
            benchmark_counting_enabled=True,
            unit_headline_eligible=True,
            conclusion="AUTO_ACCEPTED",
        )
    ]

    summary = api_smoke_ledger_projection(records)

    assert summary["benchmark_counting_enabled_records"] == 1
    assert summary["unit_headline_eligible_records"] == 1
    assert summary["need_human_review_records"] == 0
    assert summary["invariant_warnings"] == [
        "api_smoke_row_marked_benchmark_counting_enabled",
        "api_smoke_row_marked_unit_headline_eligible",
        "api_smoke_row_not_need_human_review",
    ]


def test_invalid_projection_view_is_rejected():
    with pytest.raises(ValueError, match="view"):
        api_smoke_ledger_projection([], view="unit")


def test_render_api_smoke_ledger_markdown_omits_unit_only_ledgers():
    records = [_unit_rec()]

    md = render_api_smoke_ledger_markdown(records)

    assert md == ""
    assert ledger_summary(records)["records"] == 1


def test_render_api_smoke_ledger_markdown_is_presentation_only():
    records = [
        _rec("api1", run_kind="real", smoke_id="real-smoke"),
        _rec("api2", run_kind="external", smoke_id="external-smoke"),
        _rec("api3", run_kind="fake"),
        _rec(
            "api4",
            run_kind="external",
            eligible=False,
            reasons=["api_evidence_absent"],
            requirement_failures=["api_evidence_present"],
            gen_outcome="TEST_FAILURE",
            quality_gate_status="FAIL",
            review_recommendation="REJECT_CANDIDATE",
            failure_type="TEST_FAILURE",
        ),
        _unit_rec(),
    ]
    before_summary = ledger_summary(records)
    before_badcases = [stat.model_dump() for stat in aggregate_badcases(records)]

    md = render_api_smoke_ledger_markdown(records)

    assert "## API smoke ledger - RAW (all run_kinds)" in md
    assert "## API smoke ledger - HEADLINE (S8 eligible; real/external only)" in md
    raw = md.split("## API smoke ledger - RAW (all run_kinds)", 1)[1].split("##", 1)[0]
    headline = md.split(
        "## API smoke ledger - HEADLINE (S8 eligible; real/external only)", 1
    )[1]
    assert "source_records: 4  projected_records: 4" in raw
    assert "eligible_source_records: 3  ineligible_source_records: 1" in raw
    assert "'fake': 1" in raw
    assert "api_evidence_absent" in raw
    assert "source_records: 4  projected_records: 2" in headline
    assert "'real': 1" in headline and "'external': 1" in headline
    assert "'fake'" not in headline
    assert "api_evidence_absent" not in headline
    assert "accept_rate" not in md
    assert "usable_test" not in md
    assert ledger_summary(records) == before_summary
    assert [stat.model_dump() for stat in aggregate_badcases(records)] == before_badcases
