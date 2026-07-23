"""Offline tests for the Phase 2.5 benchmark harness (no Maven, no network).

Covers the pure pieces: spec parsing, failure bucketing, aggregation math, and
markdown rendering. The real judge+generate run is exercised manually via
scripts/run_benchmark.py against real repos.
"""
import pytest
import time

from app.benchmark.models import (
    COVERAGE_AVAILABLE,
    COVERAGE_UNAVAILABLE,
    BenchCase,
    BenchCaseResult,
    BenchReport,
    aggregate,
    asset_gate_breakdown,
    classify_failure,
    load_spec,
)
from app.benchmark.report_md import render_markdown
from app.benchmark.runner import _completed_result, run_benchmark
from app.llm.fake_client import FakeLLMClient
from app.models.job import Job, JobStatus

# JaCoCo double-agent crash signature (F2) and an Apache RAT failure (F1).
_JACOCO_LOG = "Caused by: java.lang.LinkageError: ... java.lang.$JaCoCo ..."
_RAT_LOG = "[ERROR] Failed to execute goal org.apache.rat:apache-rat-plugin:0.18:check"


def test_load_spec_ok():
    cases = load_spec({"cases": [
        {"name": "x", "repo_url": "u", "target_class": "C", "target_method": "m"},
        {"repo_url": "u2", "target_class": "D"},
    ]})
    assert len(cases) == 2
    assert cases[0].label() == "x"
    assert cases[1].label() == "D#*"  # no name, no method


def test_load_spec_rejects_empty():
    with pytest.raises(ValueError):
        load_spec({"cases": []})
    with pytest.raises(ValueError):
        load_spec({})


def test_classify_failure_buckets():
    assert classify_failure(False, "REPO_NOT_BUILDABLE", None) == "REPO_NOT_BUILDABLE"
    assert classify_failure(True, "GEN_FAILED", None) == "PIPELINE_FAILED"
    assert classify_failure(True, "GEN_DONE", "COMPILE_FAILURE") == "COMPILE_FAILURE"
    assert classify_failure(True, "GEN_DONE", "TEST_FAILURE") == "TEST_FAILURE"
    assert classify_failure(True, "GEN_DONE", "PASS") is None  # clean pass


def test_classify_failure_unmasks_jacoco_conflict():
    # F2 surfaces as NO_TESTS at the coarse level, but the log reveals the crash.
    assert classify_failure(True, "GEN_DONE", "NO_TESTS", _JACOCO_LOG) == "JACOCO_CONFLICT"


def test_classify_failure_unmasks_policy_plugin():
    # F1: RAT fails the build -> coarse BUILD_ERROR, log reveals the policy plugin.
    assert classify_failure(True, "GEN_DONE", "BUILD_ERROR", _RAT_LOG) == "POLICY_PLUGIN_FAILURE"


def _pass(name="p", **kw):
    base = dict(
        name=name, repo_url="u", target_class="C", repo_judged=True,
        generation_status="GEN_DONE", gen_outcome="PASS", compiled=True,
        executed=True, passed=True, coverage_dropped=False, target_improved=True,
        coverage_status=COVERAGE_AVAILABLE,
        conclusion="NEED_HUMAN_REVIEW", runtime_ms=1000, failure_type=None,
        quality_gate_status="PASS", quality_blockers=0, quality_warnings=0,
    )
    base.update(kw)
    return BenchCaseResult(**base)


def _api_smoke_review_summary(
    *,
    run_kind="external",
    eligible=True,
    smoke_id="s7c-junit-api-001",
    reasons=None,
    redline_flags=None,
    redlines_satisfied=True,
):
    summary = {
        "api_smoke_denominator": {
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
                "manifest_status_allowed": eligible,
                "candidate_kind_matches": True,
                "target_matches_generation": True,
                "api_evidence_present": eligible,
                "runner_tool_matches": True if eligible else None,
                "redaction_contract_satisfied": True if eligible else None,
                "maven_judge_evidence_present": True,
                "conclusion_needs_review": True,
                "trusted_false": True,
            },
        }
    }
    if redline_flags is not None:
        summary["api_smoke_redlines"] = {
            "summary_version": "api_smoke_redline_summary.v1",
            "review_flags": redline_flags,
            "redlines_satisfied": redlines_satisfied,
            "digest_signal": False,
            "verdict_authority": False,
            "trusted_authority": False,
        }
    return summary


def test_aggregate_rates_over_attempted():
    cases = [
        _pass("a"),
        _pass("b", gen_outcome="COMPILE_FAILURE", compiled=False, executed=False,
              passed=False, target_improved=None, coverage_dropped=None,
              coverage_status=COVERAGE_UNAVAILABLE, failure_type="COMPILE_FAILURE",
              quality_gate_status="FAIL", quality_blockers=1),
        _pass("r", repair_rounds=1, coverage_status=COVERAGE_UNAVAILABLE,
              target_improved=None, coverage_dropped=None),
        BenchCaseResult(name="c", repo_url="u2", target_class="D",
                        repo_judged=False, generation_status="REPO_NOT_BUILDABLE",
                        failure_type="REPO_NOT_BUILDABLE", runtime_ms=500),
    ]
    a = aggregate(cases)
    assert a["total_cases"] == 4
    assert a["repos"] == 2 and a["buildable_repos"] == 1
    assert a["setup_failures"] == 0
    assert a["clone_failures"] == 0
    assert a["repo_build_failures"] == 1
    assert a["generation_attempted"] == 3          # unbuildable excluded
    assert a["compile_pass_rate"] == 0.6667        # 2 of 3 attempted compiled
    assert a["gen_test_pass_rate"] == 0.6667
    # only the PASS case has coverage available; compile-fail case is unavailable
    assert a["coverage_measured"] == 1
    assert a["coverage_improved_rate"] == 1.0      # over coverage-available cases
    assert a["need_human_review_rate"] == 1.0      # both attempted concluded review
    assert a["top_failure_types"] == {"COMPILE_FAILURE": 1, "REPO_NOT_BUILDABLE": 1}
    assert a["average_repair_rounds"] == 1.0
    assert a["quality_gate_pass_rate"] == 0.6667
    assert a["quality_gate_failures"] == 1
    assert a["quality_gate_reviews"] == 0
    assert a["accept_rate"] is None                 # Phase 4


def test_coverage_unavailable_excluded_from_coverage_rates():
    # A clean PASS but coverage skipped (F2 avoidance) -> measured count 0, rate None.
    cases = [_pass("a", coverage_status=COVERAGE_UNAVAILABLE,
                   target_improved=None, coverage_dropped=None)]
    a = aggregate(cases)
    assert a["coverage_measured"] == 0
    assert a["coverage_improved_rate"] is None
    assert a["compile_pass_rate"] == 1.0           # compile/exec still measured


def test_aggregate_empty():
    a = aggregate([])
    assert a["total_cases"] == 0
    assert a["compile_pass_rate"] is None


def test_aggregate_run_kind_real_excludes_non_real():
    # docs/43 S2: the headline (real) view excludes fake/dryrun/smoke AND historical
    # None (unknown); the default (no filter) stays raw all-kinds for back-compat.
    cases = [
        _pass("real_ok", run_kind="real"),
        _pass("real_cf", run_kind="real", gen_outcome="COMPILE_FAILURE",
              compiled=False, executed=False, passed=False, target_improved=None,
              coverage_dropped=None, coverage_status=COVERAGE_UNAVAILABLE,
              failure_type="COMPILE_FAILURE", quality_gate_status="FAIL",
              quality_blockers=1),
        _pass("fake1", run_kind="fake"),
        _pass("dry1", run_kind="dryrun"),
        _pass("smoke1", run_kind="smoke"),
        _pass("hist", run_kind=None),            # historical / unknown
    ]
    raw = aggregate(cases)                         # back-compat: all kinds
    real = aggregate(cases, run_kind="real")       # headline
    assert raw["run_kind_filter"] is None and raw["total_cases"] == 6
    assert real["run_kind_filter"] == "real"
    assert real["total_cases"] == 2                # only the two real rows
    assert real["generation_attempted"] == 2
    assert real["compile_pass_rate"] == 0.5        # 1 of 2 real compiled
    assert real["gen_test_pass_rate"] == 0.5


def test_asset_gate_breakdown_composes_with_run_kind_without_headline_change():
    cases = [
        _pass("real_unit", run_kind="real", asset_test_level_recommendation="unit"),
        _pass(
            "real_manual",
            run_kind="real",
            asset_test_level_recommendation="manual_oracle_first",
            asset_missing_count=2,
            asset_partial_count=1,
        ),
        _pass(
            "fake_api",
            run_kind="fake",
            asset_test_level_recommendation="api",
            asset_missing_count=1,
        ),
        _pass("real_unknown", run_kind="real"),
    ]
    before_keys = set(aggregate(cases).keys())

    raw = asset_gate_breakdown(cases)
    real = asset_gate_breakdown(cases, run_kind="real")

    assert raw == {
        "run_kind_filter": None,
        "total": 4,
        "by_test_level": {
            "unit": 1,
            "manual_oracle_first": 1,
            "api": 1,
            "unknown": 1,
        },
        "missing_asset_cases": 2,
        "partial_asset_cases": 1,
        "missing_assets_total": 3,
        "partial_assets_total": 1,
    }
    assert real == {
        "run_kind_filter": "real",
        "total": 3,
        "by_test_level": {
            "unit": 1,
            "manual_oracle_first": 1,
            "unknown": 1,
        },
        "missing_asset_cases": 1,
        "partial_asset_cases": 1,
        "missing_assets_total": 2,
        "partial_assets_total": 1,
    }
    assert set(aggregate(cases).keys()) == before_keys
    assert "asset_gate_breakdown" not in aggregate(cases)


def test_render_markdown_has_facts():
    report = BenchReport(
        provider="fake", model="fake-1", generated_at="2026-06-06",
        cases=[_pass("a", target_branch_delta=0.5)],
        aggregate=aggregate([_pass("a", target_branch_delta=0.5)]),
    )
    md = render_markdown(report)
    assert "Real-Repo Benchmark Report" in md
    assert "compile_pass_rate" in md
    assert "quality_gate_pass_rate" in md
    assert "setup_failures" in md
    assert "deepseek" not in md.lower()  # no hardcoded model
    assert "| a |" in md
    # docs/43 S2: both the raw and the real-only headline aggregate sections render
    assert "RAW (all run_kinds)" in md
    assert "HEADLINE (real only" in md
    assert "fake/dryrun/smoke/external/unknown excluded" in md


def test_render_markdown_includes_asset_gate_breakdown_without_headline_drift():
    cases = [
        _pass(
            "real_manual",
            run_kind="real",
            asset_test_level_recommendation="manual_oracle_first",
            asset_missing_count=2,
            asset_partial_count=1,
        ),
        _pass("real_unit", run_kind="real", asset_test_level_recommendation="unit"),
        _pass(
            "fake_api",
            run_kind="fake",
            asset_test_level_recommendation="api",
            asset_missing_count=1,
        ),
        _pass("historical_unknown", run_kind=None),
    ]
    before_keys = set(aggregate(cases).keys())

    md = render_markdown(BenchReport(cases=cases, aggregate=aggregate(cases)))

    assert "## Asset Gate - RAW (all run_kinds)" in md
    assert "## Asset Gate - HEADLINE (real only)" in md
    raw = md.split("## Asset Gate - RAW (all run_kinds)", 1)[1].split("##", 1)[0]
    headline = md.split("## Asset Gate - HEADLINE (real only)", 1)[1].split("##", 1)[0]
    assert "- total: 4  (run_kind_filter: None)" in raw
    assert "api" in raw
    assert "missing_asset_cases: 2  missing_assets_total: 3" in raw
    assert "- total: 2  (run_kind_filter: real)" in headline
    assert "manual_oracle_first" in headline and "unit" in headline
    assert "api" not in headline
    assert "missing_asset_cases: 1  missing_assets_total: 2" in headline
    assert set(aggregate(cases).keys()) == before_keys
    assert "asset_gate_breakdown" not in aggregate(cases)


def test_render_markdown_includes_validation_line_without_aggregate_drift():
    cases = [
        _pass("real_ok", run_kind="real"),
        _pass(
            "real_weak",
            run_kind="real",
            gen_outcome="COMPILE_FAILURE",
            compiled=False,
            executed=False,
            passed=False,
            failure_type="COMPILE_FAILURE",
            quality_gate_status="FAIL",
            quality_blockers=1,
            review_summary={
                "quality": {
                    "status": "FAIL",
                    "blockers": ["no_assertions"],
                    "warnings": [],
                },
            },
        ),
        _pass("fake_ok", run_kind="fake"),
    ]
    before_keys = set(aggregate(cases).keys())

    md = render_markdown(BenchReport(cases=cases, aggregate=aggregate(cases)))

    assert "## Real-world validation line - RAW (all run_kinds)" in md
    assert "## Real-world validation line - HEADLINE (real only)" in md
    raw = md.split(
        "## Real-world validation line - RAW (all run_kinds)", 1
    )[1].split("##", 1)[0]
    headline = md.split(
        "## Real-world validation line - HEADLINE (real only)", 1
    )[1].split("##", 1)[0]
    assert "first_run_evidence_cases: 3  (run_kind_filter: None)" in raw
    assert "first_compile_pass_rate: 67%" in raw
    assert "first_run_evidence_cases: 2  (run_kind_filter: real)" in headline
    assert "first_compile_pass_rate: 50%" in headline
    assert "structural_weak_signal_cases: 1/2" in headline
    assert "human/golden metrics remain unavailable" in headline
    assert set(aggregate(cases).keys()) == before_keys
    assert "first_compile_pass_rate" not in aggregate(cases)


def test_render_markdown_omits_api_smoke_sections_without_source_rows():
    cases = [_pass("unit_only", run_kind="real")]

    md = render_markdown(BenchReport(cases=cases, aggregate=aggregate(cases)))

    assert "API smoke denominator" not in md


def test_render_markdown_includes_api_smoke_projection_without_headline_drift():
    cases = [
        _pass(
            "real_api",
            run_kind="real",
            review_summary=_api_smoke_review_summary(
                run_kind="real",
                smoke_id="real-smoke",
                redline_flags=[],
            ),
        ),
        _pass(
            "external_api",
            run_kind="external",
            review_summary=_api_smoke_review_summary(
                run_kind="external",
                smoke_id="external-smoke",
                redline_flags=["runner_tool_mismatch"],
                redlines_satisfied=False,
            ),
        ),
        _pass(
            "fake_api",
            run_kind="fake",
            review_summary=_api_smoke_review_summary(
                run_kind="fake",
                redline_flags=["fake_only"],
                redlines_satisfied=False,
            ),
        ),
        _pass(
            "external_ineligible",
            run_kind="external",
            gen_outcome="TEST_FAILURE",
            passed=False,
            failure_type="TEST_FAILURE",
            quality_gate_status="FAIL",
            review_recommendation="REJECT_CANDIDATE",
            review_summary=_api_smoke_review_summary(
                run_kind="external",
                eligible=False,
                reasons=["api_evidence_absent"],
                redline_flags=["api_evidence_absent"],
                redlines_satisfied=False,
            ),
        ),
        _pass("real_unit", run_kind="real"),
    ]
    before_keys = set(aggregate(cases).keys())

    md = render_markdown(BenchReport(cases=cases, aggregate=aggregate(cases)))

    assert "## API smoke denominator - RAW (all run_kinds)" in md
    assert "## API smoke denominator - HEADLINE (S8 eligible; real/external only)" in md
    raw = md.split(
        "## API smoke denominator - RAW (all run_kinds)", 1
    )[1].split("##", 1)[0]
    headline = md.split(
        "## API smoke denominator - HEADLINE (S8 eligible; real/external only)", 1
    )[1].split("##", 1)[0]
    aggregate_headline = md.split(
        "HEADLINE (real only; fake/dryrun/smoke/external/unknown excluded)", 1
    )[1].split("##", 1)[0]

    assert "source_rows: 4  projected_rows: 4" in raw
    assert "eligible_source_rows: 3  ineligible_source_rows: 1" in raw
    assert "'external': 2" in raw and "'real': 1" in raw and "'fake': 1" in raw
    assert "api_evidence_absent" in raw
    assert "redline_flag_counts: {'runner_tool_mismatch': 1" in raw
    assert "'fake_only': 1" in raw
    assert "redlines_satisfied_distribution: {'false': 3, 'true': 1}" in raw
    assert "source_rows: 4  projected_rows: 2" in headline
    assert "'external': 1" in headline and "'real': 1" in headline
    assert "'fake'" not in headline
    assert "redline_flag_counts: {'runner_tool_mismatch': 1}" in headline
    assert "redlines_satisfied_distribution: {'true': 1, 'false': 1}" in headline
    assert "fake_only" not in headline
    assert "api_evidence_absent" not in headline
    assert "accept_rate" not in raw and "accept_rate" not in headline
    assert "- total_cases: 2" in aggregate_headline
    assert set(aggregate(cases).keys()) == before_keys
    assert "api_smoke_denominator" not in aggregate(cases)


def test_render_markdown_places_api_smoke_after_validation_before_survivors():
    review_summary = _api_smoke_review_summary(run_kind="external")
    review_summary["mutation_survivors"] = {
        "total_survivors": 1,
        "counts": {"survived_weak_oracle": 1},
    }
    cases = [
        _pass(
            "external_api_with_survivor",
            run_kind="external",
            review_summary=review_summary,
        )
    ]

    md = render_markdown(BenchReport(cases=cases, aggregate=aggregate(cases)))

    assert (
        md.index("## Real-world validation line - HEADLINE (real only)")
        < md.index("## API smoke denominator - RAW (all run_kinds)")
        < md.index("## API smoke denominator - HEADLINE (S8 eligible; real/external only)")
        < md.index("## Survived mutants")
        < md.index("## Per-case")
    )


def test_completed_result_carries_review_summary_failures():
    fqcn = "com.example.CAiGeneratedTest"
    job = Job(git_url="file:///repo", status=JobStatus.GEN_DONE,
              build_outcome="SUCCESS")
    job.test_result = {"has_reports": True, "failed": 0, "errors": 0}
    job.coverage = {}
    job.generation = {
        "target": {"target_class": "com.example.C"},
        "result": {
            "test_class_name": "CAiGeneratedTest",
            "test_source": (
                "package com.example;\n"
                "import org.junit.jupiter.api.Test;\n"
                "import static org.junit.jupiter.api.Assertions.*;\n"
                "class CAiGeneratedTest {\n"
                "  @Test void fails() { assertEquals(true, false); }\n"
                "}\n"
            ),
            "trusted": False,
        },
        "write": {"created": True, "content": "", "production_code_touched": False},
        "execution": {
            "gen_outcome": "TEST_FAILURE",
            "build_outcome": "TEST_FAILURE",
            "generated_class": fqcn,
            "suite_result": {
                "failed_cases": [
                    {
                        "classname": fqcn,
                        "name": "fails",
                        "type": "failure",
                        "message": "expected: <true> but was: <false>",
                    }
                ]
            },
        },
    }

    result = _completed_result(
        BenchCase(repo_url="file:///repo", target_class="com.example.C"),
        job,
        time.monotonic(),
    )

    failure = result.review_summary["failures"][0]
    assert failure["test_name"] == "fails"
    assert failure["expected"] == "true"
    assert failure["actual"] == "false"


def test_completed_result_carries_compact_asset_gate_fields_without_aggregate_change():
    before_keys = set(aggregate([_pass("baseline")]).keys())
    job = Job(git_url="file:///repo", status=JobStatus.GEN_DONE,
              build_outcome="SUCCESS")
    job.test_result = {"has_reports": True, "failed": 0, "errors": 0}
    job.coverage = {}
    job.generation = {
        "target": {"target_class": "com.example.Calc", "target_method": "add"},
        "result": {
            "test_class_name": "CalcAiGeneratedTest",
            "test_source": (
                "package com.example;\n"
                "import org.junit.jupiter.api.Test;\n"
                "class CalcAiGeneratedTest {\n"
                "  @Test void empty() { Client client = null; client.toString(); }\n"
                "}\n"
            ),
            "trusted": False,
        },
        "write": {"created": True, "content": "", "production_code_touched": False},
        "execution": {
            "gen_outcome": "PASS",
            "build_outcome": "SUCCESS",
            "gen_total": 1,
            "gen_passed": 1,
            "gen_failed": 0,
            "gen_errors": 0,
            "gen_skipped": 0,
        },
    }

    result = _completed_result(
        BenchCase(repo_url="file:///repo", target_class="com.example.Calc", target_method="add"),
        job,
        time.monotonic(),
    )

    assert result.asset_test_level_recommendation == "manual_oracle_first"
    assert result.asset_missing_count == 1  # business_oracle
    assert result.asset_partial_count == 2  # external_dependency_mock + test_data
    assert any(
        i["asset"] == "existing_tests"
        and i["reason"] == "report-local S1 does not persist neighbor-test asset facts"
        for i in result.review_summary["asset_sufficiency"]["risk_notes"]
    )
    assert result.conclusion == "NEED_HUMAN_REVIEW"
    assert set(aggregate([result]).keys()) == before_keys


def test_run_benchmark_reports_llm_config_failure(tmp_path, monkeypatch):
    def boom(_settings):
        raise ValueError("missing key")

    monkeypatch.setattr("app.benchmark.runner.get_client", boom)
    report = run_benchmark(
        [BenchCase(repo_url="https://example.invalid/repo.git", target_class="C")],
        workdir=tmp_path,
    )

    assert report.cases[0].failure_type == "LLM_CONFIG_FAILED"
    assert "missing key" in report.cases[0].error
    assert report.aggregate["setup_failures"] == 1
    assert report.aggregate["clone_failures"] == 0
    assert report.aggregate["repo_build_failures"] == 0
    assert report.aggregate["top_failure_types"] == {"LLM_CONFIG_FAILED": 1}


def test_run_benchmark_reports_clone_failure(tmp_path, monkeypatch):
    from app.ledger.store import LedgerStore

    monkeypatch.setattr(
        "app.benchmark.runner.get_client", lambda _settings: FakeLLMClient()
    )
    # Contain the best-effort precipitation (docs/41) inside the test sandbox, and
    # assert the run's case was appended to the ledger.
    ledger_db = tmp_path / "ledger.db"
    monkeypatch.setenv("TESTAGENT_LEDGER_DB", str(ledger_db))

    def boom(_repo_url, _branch, _cache_dir, commit=None):
        raise TimeoutError("clone timed out")

    monkeypatch.setattr("app.benchmark.runner._ensure_mirror", boom)
    report = run_benchmark(
        [BenchCase(repo_url="https://example.invalid/repo.git", target_class="C")],
        workdir=tmp_path,
    )

    assert report.cases[0].failure_type == "REPO_CLONE_FAILED"
    assert "clone timed out" in report.cases[0].error
    assert report.aggregate["setup_failures"] == 0
    assert report.aggregate["clone_failures"] == 1
    # the benchmark precipitated its judged case into the durable ledger
    assert LedgerStore(ledger_db).count() == 1
