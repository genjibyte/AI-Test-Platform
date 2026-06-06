"""Phase 2 generation API (P2-T10/T09).

``POST /jobs/{id}/generate`` runs the generation pipeline on a judged job and
returns the updated job. ``GET /jobs/{id}/generation`` returns the assembled
generation report (facts + NEED_HUMAN_REVIEW). No accept/reject (Phase 4).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.common.response import ApiResponse
from app.models.job import JobStatus
from app.pipeline.generate_pipeline import run_generation
from app.report.generation_report import assemble_generation_report
from app.storage.job_repo import JobRepo

router = APIRouter(tags=["generation"])


class GenerateRequest(BaseModel):
    target_class: str
    target_method: Optional[str] = None


@router.post("/jobs/{job_id}/generate")
def post_generate(job_id: str, req: GenerateRequest) -> ApiResponse:
    repo = JobRepo()
    job = repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=409,
            detail=f"job must be judged (DONE) before generation; got {job.status.value}",
        )
    job = run_generation(job, repo, req.target_class, req.target_method)
    return ApiResponse.ok(data=job.model_dump())


@router.get("/jobs/{job_id}/generation")
def get_generation(job_id: str) -> ApiResponse:
    job = JobRepo().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if not job.generation:
        raise HTTPException(status_code=409, detail="no generation run for this job")
    return ApiResponse.ok(data=assemble_generation_report(job.generation))
