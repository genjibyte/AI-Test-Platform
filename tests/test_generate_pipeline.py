"""Tests for the Phase 2 generation pipeline + state machine (P2-T10).

Maven-free: covers the state-machine wiring and the GEN_FAILED short-circuits.
The real happy path (mvn execute + coverage) is the Phase 2 e2e (P2-T11).
"""
import pytest

from app.models.job import Job, JobStatus, can_transition
from app.pipeline.generate_pipeline import run_generation
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo

P2_CHAIN = [
    JobStatus.TARGET_SELECT,
    JobStatus.CONTEXT,
    JobStatus.GENERATE,
    JobStatus.GEN_EXECUTE,
    JobStatus.COMPARE,
]


@pytest.fixture()
def repo(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    return JobRepo(conn=get_connection(db))


def test_phase2_forward_transitions_allowed():
    assert can_transition(JobStatus.DONE, JobStatus.TARGET_SELECT)
    assert can_transition(JobStatus.TARGET_SELECT, JobStatus.CONTEXT)
    assert can_transition(JobStatus.CONTEXT, JobStatus.GENERATE)
    assert can_transition(JobStatus.GENERATE, JobStatus.GEN_EXECUTE)
    assert can_transition(JobStatus.GEN_EXECUTE, JobStatus.COMPARE)
    assert can_transition(JobStatus.COMPARE, JobStatus.GEN_DONE)


def test_every_phase2_step_can_fail():
    for s in P2_CHAIN:
        assert can_transition(s, JobStatus.GEN_FAILED)


def test_terminal_states_have_no_exit():
    assert not can_transition(JobStatus.GEN_DONE, JobStatus.GEN_FAILED)
    assert not can_transition(JobStatus.GEN_FAILED, JobStatus.TARGET_SELECT)


def test_done_cannot_skip_target_select():
    # DONE must enter via TARGET_SELECT, not jump straight to GENERATE.
    assert not can_transition(JobStatus.DONE, JobStatus.GENERATE)


def test_phase1_unaffected():
    assert can_transition(JobStatus.CREATED, JobStatus.IMPORTING)
    assert not can_transition(JobStatus.CREATED, JobStatus.DONE)


def test_generation_requires_judged_job(repo):
    job = Job(git_url="https://example.com/x.git")  # status CREATED
    repo.create(job)
    out = run_generation(job, repo, "com.example.Calc", "max")
    assert out.status == JobStatus.GEN_FAILED
    assert "judged" in (out.error or "")
    assert out.generation and out.generation["error"]


def test_generation_fails_when_workspace_missing(repo):
    # A judged job whose workspace no longer exists on disk.
    job = Job(git_url="https://example.com/x.git", status=JobStatus.DONE)
    repo.create(job)
    out = run_generation(job, repo, "com.example.Calc", "max")
    assert out.status == JobStatus.GEN_FAILED
    assert "workspace" in (out.error or "")
