"""Tests for isolated workspace (P1-T03)."""
from app.runtime.workspace import Workspace


def test_workspaces_are_isolated(tmp_path):
    a = Workspace("job-a", root=tmp_path).create()
    b = Workspace("job-b", root=tmp_path).create()
    assert a.root != b.root
    (a.repo_dir).mkdir(parents=True, exist_ok=True)
    (a.repo_dir / "marker.txt").write_text("a", encoding="utf-8")
    assert not (b.repo_dir / "marker.txt").exists()


def test_create_and_cleanup(tmp_path):
    ws = Workspace("job-c", root=tmp_path).create()
    assert ws.exists()
    assert ws.logs_dir.exists()
    ws.cleanup()
    assert not ws.exists()
