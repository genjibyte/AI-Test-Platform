"""Per-job isolated workspace (P1-T03).

Layout under ``<workspace_root>/<job_id>/``::

    repo/   -> cloned target repository (P1-T04)
    logs/   -> per-stage execution logs (P1-T03)

Two jobs never share a directory, guaranteeing reproducible, side-effect-free
judging runs.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, Union

from app.config import get_settings


class Workspace:
    def __init__(self, job_id: str, root: Optional[Union[str, Path]] = None):
        base = Path(root) if root else get_settings().workspace_root
        self.job_id = job_id
        self.root = base / job_id

    @property
    def repo_dir(self) -> Path:
        return self.root / "repo"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    def create(self) -> "Workspace":
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        return self

    def log_file(self, name: str) -> Path:
        return self.logs_dir / name

    def exists(self) -> bool:
        return self.root.exists()

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
