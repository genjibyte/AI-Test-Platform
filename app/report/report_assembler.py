"""Read-only report assembly (P1-T10).

Aggregates a job's judging results into one structured, machine-readable report:
project info, buildability, test verdict, coverage baseline, stage log entries.

Phase 1 stops at facts — NO adoption recommendation / quality gate (that is a
later AI-phase deliverable).
"""
from __future__ import annotations

from app.models.job import Job

_BUILDABLE = {"SUCCESS", "TEST_FAILURE"}  # compiled & ran


def _stage_view(stage: dict) -> dict:
    exit_code = stage.get("exit_code")
    return {
        "name": stage.get("name"),
        "exit_code": exit_code,
        "timed_out": stage.get("timed_out", False),
        "duration_ms": stage.get("duration_ms", 0),
        "success": exit_code == 0 and not stage.get("timed_out", False),
        "log": f"/jobs/{stage.get('_job_id', '')}/logs/{stage.get('name')}"
        if stage.get("log_path")
        else None,
    }


def assemble_report(job: Job) -> dict:
    tests = job.test_result or {}
    tests_green = bool(
        tests.get("has_reports")
        and tests.get("failed", 0) == 0
        and tests.get("errors", 0) == 0
    )
    stages = []
    for s in job.stages:
        s = {**s, "_job_id": job.id}
        stages.append(_stage_view(s))

    return {
        "job_id": job.id,
        "git_url": job.git_url,
        "branch": job.branch,
        "commit_sha": job.commit_sha,
        "status": job.status.value,
        "error": job.error,
        "buildable": job.build_outcome in _BUILDABLE,
        "build_outcome": job.build_outcome,
        "tests_green": tests_green,
        "project": job.project,
        "tests": job.test_result,
        "coverage": job.coverage,
        "stages": stages,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
