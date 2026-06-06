"""Tests for per-class JaCoCo extraction + coverage comparison (P2-T08)."""
from app.coverage.coverage_compare import compare
from app.coverage.jacoco_parser import parse_jacoco, parse_jacoco_class
from app.models.coverage import Coverage

# Two classes; Calc has a partially-covered branch counter.
REPORT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<report name="demo">
  <package name="com/example">
    <class name="com/example/Calc" sourcefilename="Calc.java">
      <method name="max" desc="(II)I" line="3">
        <counter type="BRANCH" missed="1" covered="1"/>
        <counter type="LINE" missed="1" covered="2"/>
      </method>
      <counter type="BRANCH" missed="1" covered="1"/>
      <counter type="LINE" missed="1" covered="2"/>
      <counter type="METHOD" missed="0" covered="1"/>
    </class>
    <class name="com/example/Other" sourcefilename="Other.java">
      <counter type="BRANCH" missed="4" covered="0"/>
      <counter type="LINE" missed="3" covered="0"/>
      <counter type="METHOD" missed="0" covered="1"/>
    </class>
  </package>
  <counter type="BRANCH" missed="5" covered="1"/>
  <counter type="LINE" missed="4" covered="2"/>
  <counter type="METHOD" missed="0" covered="2"/>
</report>
"""


def _write(repo_dir, content=REPORT_XML):
    d = repo_dir / "target" / "site" / "jacoco"
    d.mkdir(parents=True, exist_ok=True)
    (d / "jacoco.xml").write_text(content, encoding="utf-8")


def test_parse_class_picks_class_level_counters(tmp_path):
    _write(tmp_path)
    cov = parse_jacoco_class(tmp_path, "com.example.Calc")
    assert cov.has_report
    # class-level totals, NOT the nested method counters duplicated
    assert cov.line_covered == 2 and cov.line_missed == 1
    assert cov.branch_covered == 1 and cov.branch_missed == 1
    assert cov.branch_rate == 0.5


def test_parse_class_absent(tmp_path):
    _write(tmp_path)
    assert not parse_jacoco_class(tmp_path, "com.example.Missing").has_report


def test_overall_vs_class_differ(tmp_path):
    _write(tmp_path)
    overall = parse_jacoco(tmp_path)
    calc = parse_jacoco_class(tmp_path, "com.example.Calc")
    assert overall.branch_covered == 1 and overall.branch_missed == 5  # both classes
    assert calc.branch_missed == 1                                     # Calc only


def test_compare_flags_target_improvement_no_drop():
    before = Coverage(has_report=True, line_covered=2, line_missed=2,
                      branch_covered=0, branch_missed=2)
    after = Coverage(has_report=True, line_covered=4, line_missed=0,
                     branch_covered=2, branch_missed=0)
    tbefore = Coverage(has_report=True, branch_covered=0, branch_missed=2)
    tafter = Coverage(has_report=True, branch_covered=2, branch_missed=0)
    d = compare(before, after, tbefore, tafter, "com.example.Calc")
    assert d.overall_line_delta == 0.5
    assert d.target_branch_delta == 1.0
    assert d.target_improved
    assert not d.coverage_dropped


def test_compare_detects_overall_drop():
    before = Coverage(has_report=True, line_covered=4, line_missed=0)
    after = Coverage(has_report=True, line_covered=2, line_missed=2)
    same = Coverage(has_report=True, line_covered=1, line_missed=0)
    d = compare(before, after, same, same, "com.example.Calc")
    assert d.overall_line_delta == -0.5
    assert d.coverage_dropped
    assert not d.target_improved


def test_compare_no_change_is_not_improvement():
    cov = Coverage(has_report=True, line_covered=2, line_missed=2,
                   branch_covered=1, branch_missed=1)
    d = compare(cov, cov, cov, cov, "com.example.Calc")
    assert not d.coverage_dropped
    assert not d.target_improved
    assert d.overall_line_delta == 0.0
