"""Tests for the Job model + repository (P1-T02)."""
import pytest

from app.models.job import InvalidTransition, Job, JobStatus
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo


@pytest.fixture()
def repo(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    return JobRepo(conn=get_connection(db))


def test_create_and_get(repo):
    job = Job(git_url="https://example.com/x.git", branch="main")
    repo.create(job)
    loaded = repo.get(job.id)
    assert loaded is not None
    assert loaded.git_url == "https://example.com/x.git"
    assert loaded.status == JobStatus.CREATED


def test_persists_across_connection(repo, tmp_path):
    job = Job(git_url="https://example.com/y.git")
    repo.create(job)
    # new repo / connection on the same db file
    db = repo.conn.execute("PRAGMA database_list").fetchone()[2]
    fresh = JobRepo(conn=get_connection(db))
    assert fresh.get(job.id) is not None


def test_valid_transition(repo):
    job = Job(git_url="https://example.com/z.git")
    repo.create(job)
    repo.update_status(job.id, JobStatus.IMPORTING)
    repo.update_status(job.id, JobStatus.BUILDING)
    assert repo.get(job.id).status == JobStatus.BUILDING


def test_invalid_transition_rejected(repo):
    job = Job(git_url="https://example.com/z.git")
    repo.create(job)
    with pytest.raises(InvalidTransition):
        repo.update_status(job.id, JobStatus.DONE)  # CREATED -> DONE illegal


def test_fail_from_any_state(repo):
    job = Job(git_url="https://example.com/z.git")
    repo.create(job)
    repo.update_status(job.id, JobStatus.IMPORTING)
    repo.update_status(job.id, JobStatus.FAILED, error="boom")
    loaded = repo.get(job.id)
    assert loaded.status == JobStatus.FAILED
    assert loaded.error == "boom"


def test_results_roundtrip(repo):
    job = Job(git_url="https://example.com/z.git")
    repo.create(job)
    job.test_result = {"total": 10, "passed": 9, "failed": 1}
    job.coverage = {"line": 0.42}
    repo.save(job)
    loaded = repo.get(job.id)
    assert loaded.test_result["passed"] == 9
    assert loaded.coverage["line"] == 0.42
