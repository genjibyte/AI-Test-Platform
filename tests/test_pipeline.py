"""Pipeline orchestration test (P1-T09).

Real import/detect/parse + state machine are exercised; only the Maven build
step is faked (it writes representative Surefire + JaCoCo reports).
"""
import subprocess
from pathlib import Path

import pytest

from app.build.maven_runner import BuildOutcome
from app.models.exec_record import ExecRecord
from app.models.job import Job, JobStatus
from app.pipeline import judge_pipeline
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo

POM = """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>
</project>
"""

SUREFIRE = """<?xml version="1.0"?>
<testsuite name="FooTest" tests="3" failures="0" errors="0" skipped="0">
  <testcase classname="FooTest" name="a"/>
  <testcase classname="FooTest" name="b"/>
  <testcase classname="FooTest" name="c"/>
</testsuite>
"""

JACOCO = """<?xml version="1.0"?>
<report name="demo">
  <counter type="LINE" missed="5" covered="45"/>
  <counter type="BRANCH" missed="2" covered="8"/>
  <counter type="METHOD" missed="1" covered="9"/>
</report>
"""


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def source_repo(tmp_path):
    src = tmp_path / "source"
    (src / "src/main/java").mkdir(parents=True)
    (src / "pom.xml").write_text(POM, encoding="utf-8")
    _git(["init", "-q"], src)
    _git(["config", "user.email", "t@e.com"], src)
    _git(["config", "user.name", "t"], src)
    _git(["add", "-A"], src)
    _git(["commit", "-q", "-m", "init"], src)
    return src


def _fake_build(repo_dir, workspace, **_):
    repo_dir = Path(repo_dir)
    sd = repo_dir / "target" / "surefire-reports"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "TEST-FooTest.xml").write_text(SUREFIRE, encoding="utf-8")
    jd = repo_dir / "target" / "site" / "jacoco"
    jd.mkdir(parents=True, exist_ok=True)
    (jd / "jacoco.xml").write_text(JACOCO, encoding="utf-8")
    rec = ExecRecord(name="mvn-test-jacoco", command=["mvn"],
                     cwd=str(repo_dir), exit_code=0)
    return rec, BuildOutcome.SUCCESS


def test_pipeline_happy_path(tmp_path, source_repo, monkeypatch):
    from app.config import Settings

    ws_settings = Settings(workspace_root=tmp_path / "ws", data_dir=tmp_path / "data")
    monkeypatch.setattr(judge_pipeline, "run_mvn_test_with_coverage", _fake_build)
    monkeypatch.setattr("app.runtime.workspace.get_settings", lambda: ws_settings)

    db = tmp_path / "t.db"
    init_db(db)
    repo = JobRepo(conn=get_connection(db))
    job = Job(git_url=source_repo.as_uri())
    repo.create(job)

    result = judge_pipeline.run_pipeline(job, repo)

    assert result.status == JobStatus.DONE
    assert result.build_outcome == "SUCCESS"
    assert result.commit_sha
    assert result.project["is_maven"] is True
    assert result.test_result["total"] == 3
    assert result.test_result["passed"] == 3
    assert result.coverage["line_rate"] == 0.9
    # at least import + build stages recorded
    assert len(result.stages) >= 2


def test_pipeline_non_maven_fails(tmp_path, monkeypatch):
    from app.config import Settings

    # source repo WITHOUT a pom
    src = tmp_path / "src_no_pom"
    src.mkdir()
    _git(["init", "-q"], src)
    _git(["config", "user.email", "t@e.com"], src)
    _git(["config", "user.name", "t"], src)
    (src / "readme.txt").write_text("hi", encoding="utf-8")
    _git(["add", "-A"], src)
    _git(["commit", "-q", "-m", "init"], src)

    ws_settings = Settings(workspace_root=tmp_path / "ws", data_dir=tmp_path / "data")
    monkeypatch.setattr("app.runtime.workspace.get_settings", lambda: ws_settings)

    db = tmp_path / "t.db"
    init_db(db)
    repo = JobRepo(conn=get_connection(db))
    job = Job(git_url=src.as_uri())
    repo.create(job)

    result = judge_pipeline.run_pipeline(job, repo)
    assert result.status == JobStatus.FAILED
    assert "not a maven project" in result.error
