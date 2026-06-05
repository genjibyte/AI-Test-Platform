"""Subprocess executor with timeout + log capture (P1-T03).

Every command is run in an explicit ``cwd`` (the isolated workspace). stdout and
stderr are captured, persisted to a log file, and summarized in an ExecRecord.
The host machine outside the given ``cwd`` is never touched.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

from app.models.exec_record import ExecRecord
from app.models.job import now_iso

DEFAULT_TIMEOUT = 600  # seconds


def _to_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_command(
    name: str,
    command: Sequence[str],
    cwd: Union[str, Path],
    timeout: int = DEFAULT_TIMEOUT,
    log_path: Optional[Union[str, Path]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> ExecRecord:
    command = list(command)
    started_at = now_iso()
    t0 = time.monotonic()
    timed_out = False

    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(env) if env is not None else None,
        )
        exit_code: Optional[int] = proc.returncode
        out, err = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        out = _to_text(exc.stdout)
        err = _to_text(exc.stderr) + f"\n[TIMEOUT after {timeout}s]"

    duration_ms = int((time.monotonic() - t0) * 1000)
    finished_at = now_iso()

    if log_path is not None:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"$ {' '.join(command)}\n[cwd] {cwd}\n[exit] {exit_code} "
            f"(timed_out={timed_out}, {duration_ms}ms)\n\n"
            f"=== STDOUT ===\n{out}\n=== STDERR ===\n{err}\n",
            encoding="utf-8",
        )

    return ExecRecord(
        name=name,
        command=command,
        cwd=str(cwd),
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration_ms,
        log_path=str(log_path) if log_path is not None else None,
        started_at=started_at,
        finished_at=finished_at,
        stdout=out,
        stderr=err,
    )
