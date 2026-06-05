"""Execution record for any subprocess run inside a workspace (P1-T03)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExecRecord(BaseModel):
    """Result of one command execution (git / mvn / etc.)."""

    name: str                       # logical stage name, e.g. "import", "mvn-test"
    command: list[str]
    cwd: str
    exit_code: Optional[int] = None  # None when timed out / not finished
    timed_out: bool = False
    duration_ms: int = 0
    log_path: Optional[str] = None
    started_at: str = ""
    finished_at: str = ""

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out
