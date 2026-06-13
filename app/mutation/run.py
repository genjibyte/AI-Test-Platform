"""PIT execution helper (docs/46 S3) -- the gated layer that actually runs mutation.

This is the ONLY place that may invoke Maven/PIT, and a caller must invoke it **only when
mutation is explicitly enabled** (it is never called from the live benchmark by default).
Any failure (non-zero exit, timeout, missing report) degrades to ``available=False`` --
mutation is advisory and must NEVER block judging (like coverage_unavailable). The Maven
runner is injectable so the whole path is unit-tested offline, with PIT never invoked.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Union

from app.mutation.pit import MutationResult, build_pit_command, parse_pit_report

# PIT writes its XML report here under the (built) repo dir.
_PIT_REPORT_REL = "target/pit-reports/mutations.xml"


def run_pit(
    repo_dir: Union[str, Path],
    target_classes: str,
    target_tests: str,
    *,
    mvn: str = "mvn",
    timeout: int = 900,
    runner: Callable = subprocess.run,
) -> MutationResult:
    """Run PIT ``mutationCoverage`` in ``repo_dir`` and parse the report (docs/46 S3).

    Advisory only; never raises. ``runner`` defaults to ``subprocess.run`` but is injectable
    for offline tests (so PIT is never actually invoked under unit tests). Returns
    ``available=False`` on timeout, launch error, or a missing report."""
    repo_dir = Path(repo_dir)
    cmd = build_pit_command(target_classes, target_tests, mvn=mvn)
    try:
        runner(cmd, cwd=str(repo_dir), capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return MutationResult(available=False)
    report = repo_dir / _PIT_REPORT_REL
    if not report.exists():
        return MutationResult(available=False)
    try:
        return parse_pit_report(report.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return MutationResult(available=False)
