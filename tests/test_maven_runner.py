"""Offline tests for the mvn runner (P1-T06): outcome classification + resolution.

Real ``mvn test`` execution is exercised by the T11 end-to-end test.
"""
import os

from app.build import maven_runner
from app.build.maven_runner import (
    BuildOutcome,
    classify_outcome,
    resolve_maven,
    run_mvn_test,
)
from app.models.exec_record import ExecRecord
from app.runtime.workspace import Workspace


def _rec(exit_code, out="", timed_out=False):
    return ExecRecord(
        name="mvn-test", command=["mvn"], cwd=".",
        exit_code=exit_code, timed_out=timed_out, stdout=out,
    )


def test_classify_success():
    assert classify_outcome(_rec(0, "BUILD SUCCESS")) == BuildOutcome.SUCCESS


def test_classify_compile_failure():
    out = "[ERROR] COMPILATION ERROR : cannot find symbol"
    assert classify_outcome(_rec(1, out)) == BuildOutcome.COMPILE_FAILURE


def test_classify_test_failure():
    out = "Tests run: 5, Failures: 1, Errors: 0\nThere are test failures."
    assert classify_outcome(_rec(1, out)) == BuildOutcome.TEST_FAILURE


def test_classify_build_error():
    assert classify_outcome(_rec(1, "some unrelated error")) == BuildOutcome.BUILD_ERROR


def test_classify_timeout():
    assert classify_outcome(_rec(None, timed_out=True)) == BuildOutcome.BUILD_ERROR


def test_resolve_prefers_wrapper(tmp_path):
    name = "mvnw.cmd" if os.name == "nt" else "mvnw"
    (tmp_path / name).write_text("echo wrapper", encoding="utf-8")
    resolved = resolve_maven(tmp_path)
    assert resolved is not None
    assert name in resolved[0]


def test_no_maven_returns_outcome(tmp_path, monkeypatch):
    monkeypatch.setattr(maven_runner.shutil, "which", lambda _: None)
    # ensure no wrapper, no configured maven, no PATH maven
    from app import config
    monkeypatch.setattr(config, "get_settings",
                        lambda: config.Settings(maven_cmd=None))
    ws = Workspace("job-x", root=tmp_path / "ws").create()
    record, outcome = run_mvn_test(tmp_path, ws)
    assert record is None
    assert outcome == BuildOutcome.NO_MAVEN
