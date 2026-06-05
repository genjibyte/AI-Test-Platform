"""JaCoCo-instrumented test run (P1-T08).

Runs ``mvn test`` with the JaCoCo agent + report goals supplied *on the command
line* using a pinned plugin version. This produces both Surefire reports and
``jacoco.xml`` in a single pass WITHOUT modifying the project's pom or sources.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

from app.build.maven_runner import (
    ENCODING_ARGS,
    BuildOutcome,
    classify_outcome,
    resolve_maven,
)
from app.models.exec_record import ExecRecord
from app.runtime.executor import run_command
from app.runtime.workspace import Workspace

DEFAULT_JACOCO_VERSION = "0.8.12"
DEFAULT_TEST_TIMEOUT = 1800


def build_command(base: list[str], jacoco_version: str) -> list[str]:
    plugin = f"org.jacoco:jacoco-maven-plugin:{jacoco_version}"
    return [
        *base,
        "-B",
        *ENCODING_ARGS,
        f"{plugin}:prepare-agent",
        "test",
        f"{plugin}:report",
    ]


def run_mvn_test_with_coverage(
    repo_dir: Union[str, Path],
    workspace: Workspace,
    jacoco_version: str = DEFAULT_JACOCO_VERSION,
    timeout: int = DEFAULT_TEST_TIMEOUT,
) -> Tuple[Optional[ExecRecord], BuildOutcome]:
    base = resolve_maven(repo_dir)
    if base is None:
        return None, BuildOutcome.NO_MAVEN
    cmd = build_command(base, jacoco_version)
    log = workspace.log_file("mvn-test-jacoco.log")
    record = run_command(
        "mvn-test-jacoco", cmd, cwd=repo_dir, log_path=log, timeout=timeout
    )
    return record, classify_outcome(record)
