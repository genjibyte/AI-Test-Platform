"""Mutation core tests (docs/46 S3). Offline: PIT is NEVER invoked -- we only parse a
stubbed PIT XML report and build the command string. Mutation evidence is advisory and
never changes a verdict.
"""
from app.mutation import (
    PIT_VERSION,
    build_pit_command,
    parse_pit_report,
)

_REPORT = """<?xml version="1.0" encoding="UTF-8"?>
<mutations>
  <mutation detected='true' status='KILLED'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='true' status='KILLED'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='true' status='TIMED_OUT'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='false' status='SURVIVED'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='false' status='NO_COVERAGE'><mutatedClass>com.x.Calc</mutatedClass></mutation>
</mutations>
"""


def test_parse_pit_report_counts_and_score():
    r = parse_pit_report(_REPORT)
    assert r.available is True
    assert r.total == 5 and r.detected == 3
    assert r.killed == 2 and r.timed_out == 1 and r.survived == 1 and r.no_coverage == 1
    assert r.mutation_score == 0.6           # 3 detected / 5 total
    assert r.status_counts["KILLED"] == 2


def test_parse_pit_report_unavailable_on_empty_or_malformed():
    assert parse_pit_report(None).available is False
    assert parse_pit_report("").available is False
    assert parse_pit_report("<mutations></mutations>").available is False   # zero mutations
    assert parse_pit_report("<not valid xml").available is False            # malformed
    assert parse_pit_report(None).mutation_score is None


def test_build_pit_command_is_commandline_no_pom_edit():
    cmd = build_pit_command("com.x.Calc", "com.x.CalcTest")
    assert cmd[0] == "mvn"
    assert f"org.pitest:pitest-maven:{PIT_VERSION}:mutationCoverage" in cmd
    assert "-DtargetClasses=com.x.Calc" in cmd
    assert "-DtargetTests=com.x.CalcTest" in cmd
    assert "-DoutputFormats=XML" in cmd
    # configuration is via -D only -- the command never edits a pom
    assert not any("pom" in part.lower() for part in cmd)
