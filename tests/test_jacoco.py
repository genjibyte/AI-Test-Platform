"""Tests for JaCoCo parsing + command building (P1-T08)."""
from app.coverage.jacoco_parser import parse_jacoco
from app.coverage.jacoco_runner import build_command

JACOCO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<report name="demo">
  <counter type="INSTRUCTION" missed="10" covered="90"/>
  <counter type="BRANCH" missed="2" covered="8"/>
  <counter type="LINE" missed="5" covered="45"/>
  <counter type="METHOD" missed="1" covered="9"/>
  <counter type="CLASS" missed="0" covered="3"/>
</report>
"""


def _write_jacoco(repo_dir, content=JACOCO_XML):
    d = repo_dir / "target" / "site" / "jacoco"
    d.mkdir(parents=True, exist_ok=True)
    (d / "jacoco.xml").write_text(content, encoding="utf-8")


def test_parse_jacoco(tmp_path):
    _write_jacoco(tmp_path)
    cov = parse_jacoco(tmp_path)
    assert cov.has_report
    assert cov.line_covered == 45
    assert cov.line_missed == 5
    assert cov.line_rate == 0.9
    assert cov.branch_rate == 0.8
    assert cov.method_rate == 0.9


def test_no_report(tmp_path):
    cov = parse_jacoco(tmp_path)
    assert not cov.has_report
    assert cov.line_rate == 0.0


def test_summary_includes_rates(tmp_path):
    _write_jacoco(tmp_path)
    s = parse_jacoco(tmp_path).summary()
    assert s["line_rate"] == 0.9
    assert s["branch_rate"] == 0.8


def test_build_command_positions_goals():
    cmd = build_command(["mvn"], "0.8.12")
    pa = cmd.index("org.jacoco:jacoco-maven-plugin:0.8.12:prepare-agent")
    test = cmd.index("test")
    report = cmd.index("org.jacoco:jacoco-maven-plugin:0.8.12:report")
    assert pa < test < report
