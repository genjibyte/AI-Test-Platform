"""Phase 1 end-to-end with REAL Maven (P1-T11).

Two gated (``TESTAGENT_E2E=1``) tests:

1. ``test_real_build_and_parse`` — runs real ``mvn test`` + JaCoCo against the
   committed ``samples/calc`` fixture and parses the REAL reports. This validates
   the judging core (T06+T07+T08) against actual Maven output.

2. ``test_full_pipeline_git`` — the complete pipeline including git import. It
   self-skips if the host's security agent tampers cloned files (see
   docs/10_phase1/06_PHASE1_GOLDEN_SAMPLE.md), since that corrupts the cloned source.

Run::

    set TESTAGENT_MAVEN_CMD=...\\mvn.cmd
    set TESTAGENT_E2E=1
    pytest tests/e2e -s
"""
import os
import subprocess
from pathlib import Path

import pytest

from app.build.maven_runner import BuildOutcome, resolve_maven
from app.coverage.jacoco_parser import parse_jacoco
from app.coverage.jacoco_runner import run_mvn_test_with_coverage
from app.models.job import Job, JobStatus
from app.pipeline import judge_pipeline
from app.report.surefire_parser import parse_surefire
from app.runtime.workspace import Workspace
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo

pytestmark = pytest.mark.skipif(
    os.environ.get("TESTAGENT_E2E") != "1", reason="set TESTAGENT_E2E=1 to run"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "samples" / "calc"


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True, text=True)


def _maven_or_skip(probe_dir):
    if resolve_maven(probe_dir) is None:
        pytest.skip("maven not resolvable (set TESTAGENT_MAVEN_CMD)")


def test_real_build_and_parse(tmp_path):
    """Real mvn + JaCoCo on the committed fixture, then parse real reports."""
    _maven_or_skip(SAMPLE)
    ws = Workspace("e2e-build", root=tmp_path / "ws").create()

    record, outcome = run_mvn_test_with_coverage(SAMPLE, ws)

    assert record is not None
    assert outcome == BuildOutcome.SUCCESS, (record.stdout or "")[-2000:]

    tests = parse_surefire(SAMPLE)
    coverage = parse_jacoco(SAMPLE)
    assert tests.has_reports and tests.total == 2 and tests.passed == 2
    assert coverage.has_report and coverage.line_covered > 0
    assert 0.0 < coverage.line_rate <= 1.0


@pytest.mark.skipif(
    os.environ.get("TESTAGENT_E2E_GIT") != "1",
    reason="git-clone e2e needs a non-file-tampering host; set TESTAGENT_E2E_GIT=1",
)
def test_full_pipeline_git(tmp_path, monkeypatch):
    """Full pipeline incl. git import; skips if host tampers cloned files."""
    _maven_or_skip(tmp_path)

    base = Path(os.environ.get("TESTAGENT_E2E_BASE") or tmp_path)
    base.mkdir(parents=True, exist_ok=True)

    from app.config import Settings

    settings = Settings(
        workspace_root=base / "ws",
        data_dir=base / "data",
        maven_cmd=os.environ.get("TESTAGENT_MAVEN_CMD"),
    )
    monkeypatch.setattr("app.runtime.workspace.get_settings", lambda: settings)

    # Build a source repo by checking the committed fixture into a fresh git repo.
    src = base / "sample_src"
    if src.exists():
        import shutil
        shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    _copy_tree(SAMPLE, src)
    _git(["init", "-q"], src)
    _git(["config", "user.email", "t@e.com"], src)
    _git(["config", "user.name", "t"], src)
    _git(["add", "-A"], src)
    _git(["commit", "-q", "-m", "sample"], src)

    db = base / "e2e.db"
    init_db(db)
    repo = JobRepo(conn=get_connection(db))
    job = Job(git_url=src.as_uri())
    repo.create(job)
    job = judge_pipeline.run_pipeline(job, repo)

    cloned = Workspace(job.id).repo_dir / "src/main/java/com/example/Calc.java"
    if cloned.is_file() and "class Calc" not in cloned.read_text(
        encoding="utf-8", errors="replace"
    ):
        pytest.skip("host security agent tampered cloned files; run on non-DLP host")

    assert job.status == JobStatus.DONE, job.error
    assert job.build_outcome == "SUCCESS"
    assert job.test_result["passed"] == 2
    assert job.coverage["has_report"] is True


def _copy_tree(src: Path, dst: Path):
    """Recreate the fixture by READING (intact) and WRITING via python.

    NOTE: on a file-tampering host the python-written copies may be stubbed;
    that is exactly what test_full_pipeline_git detects and skips on.
    """
    for path in src.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
