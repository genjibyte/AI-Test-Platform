"""Tests for git import (P1-T04). Uses a local source repo — no network."""
import subprocess

import pytest

from app.importer.git_importer import import_repo, read_commit
from app.runtime.workspace import Workspace


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def source_repo(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    _git(["init", "-q"], src)
    _git(["config", "user.email", "t@example.com"], src)
    _git(["config", "user.name", "tester"], src)
    (src / "App.java").write_text("class App {}", encoding="utf-8")
    _git(["add", "-A"], src)
    _git(["commit", "-q", "-m", "init"], src)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(src),
                          capture_output=True, text=True).stdout.strip()
    return src, head


def test_import_success(tmp_path, source_repo):
    src, head = source_repo
    ws = Workspace("job-import", root=tmp_path / "ws")
    record, commit = import_repo(src.as_uri(), ws)
    assert record.success
    assert (ws.repo_dir / "App.java").exists()
    assert commit == head
    assert ws.log_file("import.log").exists()


def test_import_failure_is_graceful(tmp_path):
    ws = Workspace("job-bad", root=tmp_path / "ws")
    record, commit = import_repo(
        "file:///nonexistent/repo/path.git", ws, timeout=30
    )
    assert not record.success
    assert commit is None
