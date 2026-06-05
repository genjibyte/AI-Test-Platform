"""Git repository import into the isolated workspace (P1-T04).

Clones a public https (or local) repo at an optional branch into
``workspace.repo_dir`` and reads the resulting commit SHA. Read-only with
respect to the source: the platform never writes back to the origin.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

from app.models.exec_record import ExecRecord
from app.runtime.executor import run_command
from app.runtime.workspace import Workspace


def clone_repo(
    git_url: str,
    dest: Union[str, Path],
    branch: Optional[str] = None,
    log_path: Optional[Union[str, Path]] = None,
    timeout: int = 600,
) -> ExecRecord:
    dest = Path(dest)
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch, "--single-branch"]
    cmd += [git_url, str(dest)]
    return run_command(
        "git-clone", cmd, cwd=dest.parent, log_path=log_path, timeout=timeout
    )


def read_commit(repo_dir: Union[str, Path]) -> Optional[str]:
    rec = run_command(
        "git-rev-parse",
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        cwd=repo_dir,
    )
    if rec.success and rec.stdout:
        return rec.stdout.strip()
    return None


def import_repo(
    git_url: str,
    workspace: Workspace,
    branch: Optional[str] = None,
    timeout: int = 600,
) -> Tuple[ExecRecord, Optional[str]]:
    """Clone into the job workspace. Returns (clone_record, commit_sha|None)."""
    workspace.create()
    dest = workspace.repo_dir
    log = workspace.log_file("import.log")
    record = clone_repo(git_url, dest, branch=branch, log_path=log, timeout=timeout)
    commit = read_commit(dest) if record.success else None
    return record, commit
