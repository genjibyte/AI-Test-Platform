"""Tests for Surefire parsing (P1-T07)."""
from app.report.surefire_parser import parse_surefire

SUITE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.FooTest" tests="3" failures="1" errors="0" skipped="0" time="0.1">
  <testcase classname="com.example.FooTest" name="testA" time="0.01"/>
  <testcase classname="com.example.FooTest" name="testB" time="0.01">
    <failure message="expected 1 but was 2" type="java.lang.AssertionError">stack</failure>
  </testcase>
  <testcase classname="com.example.FooTest" name="testC" time="0.01"/>
</testsuite>
"""


def _write_report(repo_dir, name, content):
    d = repo_dir / "target" / "surefire-reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content, encoding="utf-8")


def test_parse_single_suite(tmp_path):
    _write_report(tmp_path, "TEST-com.example.FooTest.xml", SUITE_XML)
    result = parse_surefire(tmp_path)
    assert result.has_reports
    assert result.total == 3
    assert result.passed == 2
    assert result.failed == 1
    assert result.errors == 0
    assert not result.green
    assert len(result.failed_cases) == 1
    fc = result.failed_cases[0]
    assert fc.name == "testB"
    assert fc.type == "failure"
    assert "expected 1" in fc.message


def test_no_reports(tmp_path):
    result = parse_surefire(tmp_path)
    assert not result.has_reports
    assert result.total == 0
    assert not result.green


def test_all_green(tmp_path):
    green = SUITE_XML.replace('tests="3" failures="1"', 'tests="3" failures="0"')
    green = green.replace(
        '<failure message="expected 1 but was 2" '
        'type="java.lang.AssertionError">stack</failure>',
        "",
    )
    _write_report(tmp_path, "TEST-com.example.FooTest.xml", green)
    result = parse_surefire(tmp_path)
    assert result.green
    assert result.failed == 0
    assert result.passed == 3
