"""Job entity + state machine (P1-T02).

A Job is one judging run over a target repository. Phase 1 state machine::

    CREATED -> IMPORTING -> BUILDING -> PARSING -> DONE
                  |            |           |
                  +------------+-----------+--> FAILED   (terminal)

DONE and FAILED are terminal. No Generate/Fix states exist in Phase 1.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, enum.Enum):
    CREATED = "CREATED"
    IMPORTING = "IMPORTING"
    BUILDING = "BUILDING"
    PARSING = "PARSING"
    DONE = "DONE"
    FAILED = "FAILED"


# Allowed forward transitions. Any non-terminal state may also go to FAILED.
_ALLOWED: dict[JobStatus, set[JobStatus]] = {
    JobStatus.CREATED: {JobStatus.IMPORTING, JobStatus.FAILED},
    JobStatus.IMPORTING: {JobStatus.BUILDING, JobStatus.FAILED},
    JobStatus.BUILDING: {JobStatus.PARSING, JobStatus.FAILED},
    JobStatus.PARSING: {JobStatus.DONE, JobStatus.FAILED},
    JobStatus.DONE: set(),
    JobStatus.FAILED: set(),
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

    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
