"""Target selection + context snapshot API (P2-T01). Read-only.

NO LLM, NO generation. Just lists classes, reads a class structure, and builds
the bounded Context Snapshot for a user-specified target.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.common.response import ApiResponse
from app.context.class_index import list_classes
from app.context.context_collector import ContextError, build_snapshot
from app.runtime.workspace import Workspace
from app.storage.job_repo import JobRepo
from app.targeting.target_selector import resolve_target

router = APIRouter(tags=["context"])


def _repo_dir(job_id: str):
    job = JobRepo().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    repo_dir = Workspace(job.id).repo_dir
    if not repo_dir.is_dir():
        raise HTTPException(status_code=409, detail="job workspace not imported")
    return repo_dir


class ContextRequest(BaseModel):
    target_class: str
    target_method: Optional[str] = None


@router.get("/jobs/{job_id}/classes")
def get_classes(job_id: str) -> ApiResponse:
    refs = list_classes(_repo_dir(job_id))
    return ApiResponse.ok(data=[r.model_dump() for r in refs])


@router.get("/jobs/{job_id}/classes/{fqn}")
def get_class(job_id: str, fqn: str) -> ApiResponse:
    target, structure = resolve_target(_repo_dir(job_id), fqn)
    if not target.exists or structure is None:
        raise HTTPException(status_code=404, detail=target.reason or "class not found")
    return ApiResponse.ok(data=structure.model_dump())


@router.post("/jobs/{job_id}/context")
def post_context(job_id: str, req: ContextRequest) -> ApiResponse:
    repo_dir = _repo_dir(job_id)
    try:
        snapshot = build_snapshot(repo_dir, req.target_class, req.target_method)
    except ContextError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ApiResponse.ok(data=snapshot.model_dump())
