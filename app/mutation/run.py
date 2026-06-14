"""PIT execution helper (docs/46 S3) -- the gated layer that actually runs mutation.

This is the ONLY place that may invoke Maven/PIT, and a caller must invoke it **only when
mutation is explicitly enabled** (it is never called from the live benchmark by default).
Any failure (non-zero exit, timeout, missing report) degrades to ``available=False`` --
mutation is advisory and must NEVER block judging (like coverage_unavailable). The Maven
runner is injectable so the whole path is unit-tested offline, with PIT never invoked.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Union

from app.mutation.pit import (
    PIT_VERSION,
    MutationResult,
    build_pit_command,
    build_pit_pom,
    parse_pit_report,
)

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
    include_mutations: bool = False,
) -> MutationResult:
    """Run PIT ``mutationCoverage`` in ``repo_dir`` and parse the report (docs/46 S3).

    Advisory only; never raises. ``runner`` defaults to ``subprocess.run`` but is injectable
    for offline tests (so PIT is never actually invoked under unit tests). Returns
    ``available=False`` on timeout, launch error, or a missing report. ``include_mutations=True``
    (docs/48 S3) also returns per-mutation rows for line-scoped invariant verification."""
    repo_dir = Path(repo_dir)
    # Windows: bare ``mvn`` is ``mvn.cmd``; subprocess (no shell) cannot launch it and raises
    # FileNotFoundError -> available=False, so the signal would never appear on Windows.
    # Resolve to the real launcher (shutil.which honours PATHEXT) so the DEFAULT path works
    # cross-platform. Falls back to the original string when Maven is not on PATH, preserving
    # the safe degrade-to-unavailable behaviour. (docs/46 §14 finding, 2026-06-14.)
    mvn = shutil.which(mvn) or mvn
    pom = repo_dir / "pom.xml"
    try:
        if pom.exists():
            # JUnit5-aware (docs/46 §14): write a SIDECAR pom (original + pitest-maven,
            # plus pitest-junit5-plugin when JUnit5) and run it with ``-f`` -- the original
            # pom is never edited. Falls back to the plain command-line goal when no pom.
            sidecar = repo_dir / "pom-pit.xml"
            sidecar.write_text(
                build_pit_pom(
                    pom.read_text(encoding="utf-8", errors="replace"),
                    target_classes=target_classes,
                    target_tests=target_tests,
                ),
                encoding="utf-8",
            )
            cmd = [
                mvn, "-f", str(sidecar), "test-compile",
                f"org.pitest:pitest-maven:{PIT_VERSION}:mutationCoverage",
            ]
        else:
            cmd = build_pit_command(target_classes, target_tests, mvn=mvn)
    except OSError:
        return MutationResult(available=False)
    try:
        runner(cmd, cwd=str(repo_dir), capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return MutationResult(available=False)
    report = repo_dir / _PIT_REPORT_REL
    if not report.exists():
        return MutationResult(available=False)
    try:
        return parse_pit_report(
            report.read_text(encoding="utf-8", errors="replace"),
            include_mutations=include_mutations,
        )
    except OSError:
        return MutationResult(available=False)
