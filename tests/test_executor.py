"""Tests for the subprocess executor (P1-T03)."""
import sys

from app.runtime.executor import run_command


def test_captures_stdout_and_exit_code(tmp_path):
    log = tmp_path / "ok.log"
    rec = run_command(
        "echo",
        [sys.executable, "-c", "print('hello-world')"],
        cwd=tmp_path,
        log_path=log,
    )
    assert rec.success
    assert rec.exit_code == 0
    assert log.exists()
    assert "hello-world" in log.read_text(encoding="utf-8")


def test_nonzero_exit_code(tmp_path):
    rec = run_command(
        "fail",
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        cwd=tmp_path,
    )
    assert rec.exit_code == 3
    assert not rec.success


def test_timeout(tmp_path):
    rec = run_command(
        "sleep",
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        timeout=1,
    )
    assert rec.timed_out
    assert not rec.success
    assert rec.exit_code is None
