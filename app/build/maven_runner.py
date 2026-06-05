"""Original ``mvn test`` runner (P1-T06).

Prefers the project's Maven Wrapper (``mvnw`` / ``mvnw.cmd``) to reduce host
dependency; falls back to a system ``mvn`` on PATH. Runs the *original* tests
only — Phase 1 never injects generated tests, never edits pom or sources.
"""
from __future__ import annotations

import enum
import os
import shutil
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from app.models.exec_record import ExecRecord
from app.runtime.executor import run_command
from app.runtime.workspace import Workspace

DEFAULT_TEST_TIMEOUT = 1800  # 30 min

# Force UTF-8 source encoding so a non-UTF-8 host default (e.g. GBK) does not
# corrupt real-world sources. Set via -D, never by editing the pom.
ENCODING_ARGS = ["-Dproject.build.sourceEncoding=UTF-8"]


class BuildOutcome(str, enum.Enum):
    SUCCESS = "SUCCESS"
    TEST_FAILURE = "TEST_FAILURE"
    COMPILE_FAILURE = "COMPILE_FAILURE"
    BUILD_ERROR = "BUILD_ERROR"
    NO_MAVEN = "NO_MAVEN"


def resolve_maven(repo_dir: Union[str, Path]) -> Optional[List[str]]:
    """Return the maven invocation prefix, or None if maven is unavailable.

    Resolution order: project Maven Wrapper -> configured ``maven_cmd``
    -> ``mvn`` on PATH.
    """
    repo_dir = Path(repo_dir)
    wrapper_name = "mvnw.cmd" if os.name == "nt" else "mvnw"
    wrapper = repo_dir / wrapper_name
    if wrapper.is_file():
        return [str(wrapper.resolve())]

    from app.config import get_settings

    configured = get_settings().maven_cmd
    if configured and Path(configured).is_file():
        return [configured]

    exe = shutil.which("mvn")
    if exe:
        return [exe]
    return None


def classify_outcome(record: ExecRecord) -> BuildOutcome:
    if record.timed_out:
        return BuildOutcome.BUILD_ERROR
    if record.exit_code == 0:
        return BuildOutcome.SUCCESS
    out = (record.stdout or "") + "\n" + (record.stderr or "")
    if "COMPILATION ERROR" in out or "Compilation failure" in out:
        return BuildOutcome.COMPILE_FAILURE
    if "There are test failures" in out or (
        "Tests run:" in out and "Failures:" in out
    ):
        return BuildOutcome.TEST_FAILURE
    return BuildOutcome.BUILD_ERROR


def run_mvn_test(
    repo_dir: Union[str, Path],
    workspace: Workspace,
    extra_args: Optional[Sequence[str]] = None,
    timeout: int = DEFAULT_TEST_TIMEOUT,
) -> Tuple[Optional[ExecRecord], BuildOutcome]:
    base = resolve_maven(repo_dir)
    if base is None:
        return None, BuildOutcome.NO_MAVEN
    cmd = [*base, "-B", *ENCODING_ARGS, "test", *(extra_args or [])]
    log = workspace.log_file("mvn-test.log")
    record = run_command("mvn-test", cmd, cwd=repo_dir, log_path=log, timeout=timeout)
    return record, classify_outcome(record)
