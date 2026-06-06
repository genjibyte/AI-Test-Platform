"""Tests for generated-test execution classification (P2-T07).

Maven-free: exercises the report isolation + outcome mapping with synthetic
Surefire reports. The real ``mvn test`` path is covered by the Phase 2 e2e
(P2-T11), gated on ``TESTAGENT_E2E``.
"""
from app.build.maven_runner import BuildOutcome
from app.generate.gen_executor import (
    GenTestOutcome,
    _classify,
    _parse_generated_report,
    fqcn_of,
)
from app.llm.schema import TestGenerationResult

GEN_FQCN = "com.example.CalcAiGeneratedTest"


def _suite_xml(name, tests, failures=0, errors=0, skipped=0, failing_case=False):
    body = '  <testcase classname="%s" name="testRuns" time="0.01"/>\n' % name
    if failing_case:
        body = (
            '  <testcase classname="%s" name="testRuns" time="0.01">\n'
            '    <failure message="boom" type="java.lang.AssertionError">s</failure>\n'
            "  </testcase>\n" % name
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<testsuite name="%s" tests="%d" failures="%d" errors="%d" skipped="%d">\n'
        "%s</testsuite>\n" % (name, tests, failures, errors, skipped, body)
    )


def _write_report(repo_dir, fqcn, **kw):
    d = repo_dir / "target" / "surefire-reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"TEST-{fqcn}.xml").write_text(_suite_xml(fqcn, **kw), encoding="utf-8")


def test_fqcn_of_with_and_without_package():
    base = dict(
        target_class="com.example.Calc",
        test_class_name="CalcAiGeneratedTest",
        file_name="CalcAiGeneratedTest.java",
        test_source="class X {}",
    )
    assert fqcn_of(TestGenerationResult(package="com.example", **base)) == GEN_FQCN
    assert fqcn_of(TestGenerationResult(**base)) == "CalcAiGeneratedTest"


def test_parse_generated_report_counts(tmp_path):
    _write_report(tmp_path, GEN_FQCN, tests=2)
    counts = _parse_generated_report(tmp_path, GEN_FQCN)
    assert counts == {"total": 2, "failures": 0, "errors": 0, "skipped": 0}


def test_parse_generated_report_missing(tmp_path):
    assert _parse_generated_report(tmp_path, GEN_FQCN) is None


def test_no_maven_short_circuits(tmp_path):
    outcome, counts = _classify(tmp_path, GEN_FQCN, BuildOutcome.NO_MAVEN)
    assert outcome is GenTestOutcome.NO_MAVEN
    assert counts is None


def test_compile_failure_attributed_to_generated(tmp_path):
    # No report exists when test compilation fails.
    outcome, _ = _classify(tmp_path, GEN_FQCN, BuildOutcome.COMPILE_FAILURE)
    assert outcome is GenTestOutcome.COMPILE_FAILURE


def test_pass_when_report_green(tmp_path):
    _write_report(tmp_path, GEN_FQCN, tests=1)
    outcome, counts = _classify(tmp_path, GEN_FQCN, BuildOutcome.SUCCESS)
    assert outcome is GenTestOutcome.PASS
    assert counts["total"] == 1


def test_failure_when_report_red(tmp_path):
    _write_report(tmp_path, GEN_FQCN, tests=1, failures=1, failing_case=True)
    outcome, _ = _classify(tmp_path, GEN_FQCN, BuildOutcome.TEST_FAILURE)
    assert outcome is GenTestOutcome.TEST_FAILURE


def test_generated_pass_isolated_from_unrelated_suite_failure(tmp_path):
    # Some OTHER class failed -> whole-suite outcome is TEST_FAILURE, but the
    # generated test's own report is green: it must still classify as PASS.
    _write_report(tmp_path, GEN_FQCN, tests=1)
    _write_report(tmp_path, "com.example.OtherTest", tests=1, failures=1,
                  failing_case=True)
    outcome, _ = _classify(tmp_path, GEN_FQCN, BuildOutcome.TEST_FAILURE)
    assert outcome is GenTestOutcome.PASS


def test_no_tests_when_report_absent_but_build_ok(tmp_path):
    outcome, _ = _classify(tmp_path, GEN_FQCN, BuildOutcome.SUCCESS)
    assert outcome is GenTestOutcome.NO_TESTS
