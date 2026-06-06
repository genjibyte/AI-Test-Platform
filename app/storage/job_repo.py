"""Job repository: CRUD + guarded status transitions (P1-T02)."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from app.models.job import (
    InvalidTransition,
    Job,
    JobStatus,
    can_transition,
    now_iso,
)
from app.storage.db import get_connection

_COLUMNS = (
    "id, git_url, branch, commit_sha, status, error, build_outcome, "
    "project_json, test_result_json, coverage_json, stages_json, "
    "target_json, generation_json, "
    "created_at, updated_at"
)


def _dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _loads(value: Optional[str]) -> Any:
    if value is None:
        return None
    return json.loads(value)


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        git_url=row["git_url"],
        branch=row["branch"],
        commit_sha=row["commit_sha"],
        status=JobStatus(row["status"]),
        error=row["error"],
        build_outcome=row["build_outcome"],
        project=_loads(row["project_json"]),
        test_result=_loads(row["test_result_json"]),
        coverage=_loads(row["coverage_json"]),
        stages=_loads(row["stages_json"]) or [],
        target=_loads(row["target_json"]),
        generation=_loads(row["generation_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class JobRepo:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or get_connection()

    # --- writes -----------------------------------------------------------
    def create(self, job: Job) -> Job:
        with self.conn:
            self.conn.execute(
                f"INSERT INTO jobs ({_COLUMNS}) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job.id,
                    job.git_url,
                    job.branch,
                    job.commit_sha,
                    job.status.value,
                    job.error,
                    job.build_outcome,
                    _dumps(job.project),
                    _dumps(job.test_result),
                    _dumps(job.coverage),
                    _dumps(job.stages),
                    _dumps(job.target),
                    _dumps(job.generation),
                    job.created_at,
                    job.updated_at,
                ),
            )
        return job

    def save(self, job: Job) -> Job:
        """Persist all mutable fields of an existing job (no transition check)."""
        job.updated_at = now_iso()
        with self.conn:
            self.conn.execute(
                "UPDATE jobs SET git_url=?, branch=?, commit_sha=?, status=?, "
                "error=?, build_outcome=?, project_json=?, test_result_json=?, "
                "coverage_json=?, stages_json=?, target_json=?, generation_json=?, "
                "updated_at=? WHERE id=?",
                (
                    job.git_url,
                    job.branch,
                    job.commit_sha,
                    job.status.value,
                    job.error,
                    job.build_outcome,
                    _dumps(job.project),
                    _dumps(job.test_result),
                    _dumps(job.coverage),
                    _dumps(job.stages),
                    _dumps(job.target),
                    _dumps(job.generation),
                    job.updated_at,
                    job.id,
                ),
            )
        return job

    def update_status(
        self, job_id: str, new_status: JobStatus, error: Optional[str] = None
    ) -> Job:
        job = self.get(job_id)
        if job is None:
            raise KeyError(f"job not found: {job_id}")
        if job.status == new_status:
            return job
        if not can_transition(job.status, new_status):
            raise InvalidTransition(
                f"illegal transition {job.status.value} -> {new_status.value}"
            )
        job.status = new_status
        if error is not None:
            job.error = error
        return self.save(job)

    # --- reads ------------------------------------------------------------
    def get(self, job_id: str) -> Optional[Job]:
        cur = self.conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE id=?", (job_id,)
        )
        row = cur.fetchone()
        return _row_to_job(row) if row else None

    def list(self, limit: int = 100) -> list[Job]:
        cur = self.conn.execute(
            f"SELECT {_COLUMNS} FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_job(r) for r in cur.fetchall()]
