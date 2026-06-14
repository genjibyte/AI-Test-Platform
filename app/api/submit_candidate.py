"""submit_candidate API (docs/53 S1).

``POST /jobs/{id}/submit_candidate`` runs the submit pipeline on a judged job:
the caller supplies a Java test source produced by ANY producer (Claude, Codex,
DeepSeek, a human, ...), and the judge stack runs verbatim.

Hard-coded invariants enforced HERE (defense in depth -- the pipeline also enforces
them, but a malformed request is rejected at the boundary):

- ``producer_id`` required, non-empty, identifier-safe, NOT ``"fake-1"``;
- ``test_source`` required, non-empty, size-capped (256 KB);
- ``run_kind`` cannot be set by the caller; the pipeline forces ``"external"``;
- ``trusted`` is ``False`` and ``conclusion`` is ``NEED_HUMAN_REVIEW`` in the
  resulting report -- the endpoint cannot accept (docs/53 §4).
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.common.response import ApiResponse
from app.models.job import JobStatus
from app.pipeline.submit_pipeline import run_external_candidate
from app.storage.job_repo import JobRepo

router = APIRouter(tags=["submit_candidate"])

# Identifier-safe producer id grammar (docs/53 §6). Resists impersonation /
# typo-squatting / mojibake. Caller's word, but the WORD itself has to be sane.
_PRODUCER_ID_RE = re.compile(r"^[A-Za-z0-9._@:+/-]{1,128}$")
_RESERVED_PRODUCER_IDS = {"fake-1"}  # reserved for FakeLLMClient (docs/43)
_MAX_TEST_SOURCE_BYTES = 256 * 1024


class SubmitCandidateRequest(BaseModel):
    target_class: str
    target_method: Optional[str] = None
    test_source: str
    producer_id: str
    producer_meta: dict = Field(default_factory=dict)


def _validate(req: SubmitCandidateRequest) -> None:
    pid = (req.producer_id or "").strip()
    if not pid:
        raise HTTPException(status_code=422, detail="producer_id is required")
    if not _PRODUCER_ID_RE.fullmatch(pid):
        raise HTTPException(
            status_code=422,
            detail="producer_id must match ^[A-Za-z0-9._@:+/-]{1,128}$",
        )
    if pid in _RESERVED_PRODUCER_IDS:
        raise HTTPException(
            status_code=422,
            detail=f"producer_id {pid!r} is reserved (impersonation guard, docs/53 §6)",
        )
    if not (req.test_source or "").strip():
        raise HTTPException(status_code=422, detail="test_source is required")
    if len(req.test_source.encode("utf-8", errors="replace")) > _MAX_TEST_SOURCE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"test_source exceeds {_MAX_TEST_SOURCE_BYTES} bytes",
        )
    if not (req.target_class or "").strip():
        raise HTTPException(status_code=422, detail="target_class is required")


@router.post("/jobs/{job_id}/submit_candidate")
def post_submit_candidate(job_id: str, req: SubmitCandidateRequest) -> ApiResponse:
    _validate(req)
    repo = JobRepo()
    job = repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=409,
            detail=f"job must be judged (DONE) before submit_candidate; got {job.status.value}",
        )
    method = (req.target_method or "").strip() or None  # whitespace-only -> None
    job = run_external_candidate(
        job, repo,
        target_class=req.target_class.strip(),
        target_method=method,
        test_source=req.test_source,
        producer_id=req.producer_id.strip(),
        producer_meta=req.producer_meta,
    )
    return ApiResponse.ok(data=job.model_dump())
