"""Job entity + state machine (P1-T02, extended P2-T10, docs/53).

A Job is one judging run over a target repository, optionally followed by one
Phase 2 producer run (generator OR external submit) on top of the judged baseline::

    CREATED -> IMPORTING -> BUILDING -> PARSING -> DONE          (Phase 1 judging)
                  |            |           |          |
                  +------------+-----------+----------+--> FAILED  (terminal)

    DONE -> TARGET_SELECT -> CONTEXT --+--> GENERATE -> GEN_EXECUTE -> COMPARE -> GEN_DONE
                                       |
                                       +--> SUBMIT_EXECUTE      -> COMPARE -> SUBMIT_DONE
              (generator step may short-circuit to GEN_FAILED;
               submit_candidate step may short-circuit to SUBMIT_FAILED)

FAILED / GEN_DONE / GEN_FAILED / SUBMIT_DONE / SUBMIT_FAILED are terminal. Phase 1
has no Generate/Fix states; either producer path only starts from a judged (DONE)
job. The two producer paths share TARGET_SELECT and CONTEXT but never collide --
a single job picks exactly one path.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, enum.Enum):
    # Phase 1 — judging
    CREATED = "CREATED"
    IMPORTING = "IMPORTING"
    BUILDING = "BUILDING"
    PARSING = "PARSING"
    DONE = "DONE"
    FAILED = "FAILED"
    # Phase 2 — generation (starts from a judged DONE job)
    TARGET_SELECT = "TARGET_SELECT"
    CONTEXT = "CONTEXT"
    GENERATE = "GENERATE"
    GEN_EXECUTE = "GEN_EXECUTE"
    COMPARE = "COMPARE"
    GEN_DONE = "GEN_DONE"
    GEN_FAILED = "GEN_FAILED"
    # Phase 2 — external submit (docs/53). Shares TARGET_SELECT + CONTEXT with the
    # generator path but has its own EXECUTE / DONE / FAILED so audit trails record
    # which producer path a job took.
    SUBMIT_EXECUTE = "SUBMIT_EXECUTE"
    SUBMIT_DONE = "SUBMIT_DONE"
    SUBMIT_FAILED = "SUBMIT_FAILED"


# Allowed forward transitions. Any non-terminal Phase 1 state may also go to
# FAILED. Phase 2 steps short-circuit to GEN_FAILED on the generator path or
# SUBMIT_FAILED on the submit_candidate path (docs/53).
_ALLOWED: dict[JobStatus, set[JobStatus]] = {
    JobStatus.CREATED: {JobStatus.IMPORTING, JobStatus.FAILED},
    JobStatus.IMPORTING: {JobStatus.BUILDING, JobStatus.FAILED},
    JobStatus.BUILDING: {JobStatus.PARSING, JobStatus.FAILED},
    JobStatus.PARSING: {JobStatus.DONE, JobStatus.FAILED},
    JobStatus.DONE: {JobStatus.TARGET_SELECT},
    JobStatus.FAILED: set(),
    JobStatus.TARGET_SELECT: {JobStatus.CONTEXT, JobStatus.GEN_FAILED, JobStatus.SUBMIT_FAILED},
    JobStatus.CONTEXT: {
        JobStatus.GENERATE,
        JobStatus.SUBMIT_EXECUTE,
        JobStatus.GEN_FAILED,
        JobStatus.SUBMIT_FAILED,
    },
    JobStatus.GENERATE: {JobStatus.GEN_EXECUTE, JobStatus.GEN_FAILED},
    JobStatus.GEN_EXECUTE: {JobStatus.COMPARE, JobStatus.GEN_FAILED},
    JobStatus.SUBMIT_EXECUTE: {JobStatus.COMPARE, JobStatus.SUBMIT_FAILED},
    JobStatus.COMPARE: {
        JobStatus.GEN_DONE,
        JobStatus.SUBMIT_DONE,
        JobStatus.GEN_FAILED,
        JobStatus.SUBMIT_FAILED,
    },
    JobStatus.GEN_DONE: set(),
    JobStatus.GEN_FAILED: set(),
    JobStatus.SUBMIT_DONE: set(),
    JobStatus.SUBMIT_FAILED: set(),
}


class InvalidTransition(Exception):
    """Raised when an illegal state transition is attempted."""


def can_transition(src: JobStatus, dst: JobStatus) -> bool:
    return dst in _ALLOWED[src]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Job(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    git_url: str
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    status: JobStatus = JobStatus.CREATED
    error: Optional[str] = None
    build_outcome: Optional[str] = None  # BuildOutcome value (P1-T06/T09)

    # Stage results, filled by later tasks (kept as opaque dicts here).
    project: Optional[dict[str, Any]] = None        # P1-T05
    test_result: Optional[dict[str, Any]] = None    # P1-T07
    coverage: Optional[dict[str, Any]] = None       # P1-T08
    stages: list[dict[str, Any]] = Field(default_factory=list)  # P1-T03/T09

    # Phase 2 generation (P2-T10). target = resolved Target; generation = the
    # generation bundle consumed by app.report.generation_report.
    target: Optional[dict[str, Any]] = None         # P2-T01/T10
    generation: Optional[dict[str, Any]] = None     # P2-T05..T09 bundle

    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
