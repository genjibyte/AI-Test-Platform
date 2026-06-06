"""Offline tests for the Phase 2.5 benchmark harness (no Maven, no network).

Covers the pure pieces: spec parsing, failure bucketing, aggregation math, and
markdown rendering. The real judge+generate run is exercised manually via
scripts/run_benchmark.py against real repos.
"""
import pytest

from app.benchmark.models import (
    COVERAGE_AVAILABLE,
    COVERAGE_UNAVAILABLE,
    BenchCase,
    BenchCaseResult,
    BenchReport,
    aggregate,
    classify_failure,
    load_spec,
)
from app.benchmark.report_md import render_markdown
from app.benchmark.runner import run_benchmark
from app.llm.fake_client import FakeLLMClient

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


def test_render_markdown_has_facts():
    report = BenchReport(
        provider="fake", model="fake-1", generated_at="2026-06-06",
        cases=[_pass("a", target_branch_delta=0.5)],
        aggregate=aggregate([_pass("a", target_branch_delta=0.5)]),
    )
    md = render_markdown(report)
    assert "Phase 2.5 Mini-Benchmark Report" in md
    assert "compile_pass_rate" in md
    assert "quality_gate_pass_rate" in md
    assert "setup_failures" in md
    assert "deepseek" not in md.lower()  # no hardcoded model
    assert "| a |" in md


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
    monkeypatch.setattr(
        "app.benchmark.runner.get_client", lambda _settings: FakeLLMClient()
    )

    def boom(_repo_url, _branch, _cache_dir):
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
