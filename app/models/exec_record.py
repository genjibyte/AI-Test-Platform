"""Execution record for any subprocess run inside a workspace (P1-T03)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


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

    # Full captured output (in-memory). Excluded when persisting to a Job's
    # stages — only ``log_path`` is kept there to avoid DB bloat.
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def trimmed(self) -> dict:
        """Dict form without bulky stdout/stderr, for persistence."""
        return self.model_dump(exclude={"stdout", "stderr"})
