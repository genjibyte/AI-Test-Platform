"""Jobs API (P1-T04 import; extended by T09 pipeline / T10 report).

Phase 1 runs synchronously. ``POST /jobs`` creates a job and performs the
git import immediately; the full judging pipeline is wired in T09.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.common.response import ApiResponse
from app.detect.maven_detector import detect as detect_maven
from app.models.job import Job
from app.pipeline.judge_pipeline import run_pipeline
from app.runtime.workspace import Workspace
from app.storage.job_repo import JobRepo

router = APIRouter(tags=["jobs"])


class CreateJobRequest(BaseModel):
    git_url: str
    branch: Optional[str] = None


@router.post("/jobs")
def create_job(req: CreateJobRequest) -> ApiResponse:
    repo = JobRepo()
    job = Job(git_url=req.git_url, branch=req.branch)
    repo.create(job)
    job = run_pipeline(job, repo)
    return ApiResponse.ok(data=job.model_dump())


@router.get("/jobs")
def list_jobs() -> ApiResponse:
    repo = JobRepo()
    return ApiResponse.ok(data=[j.model_dump() for j in repo.list()])


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> ApiResponse:
    repo = JobRepo()
    job = repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return ApiResponse.ok(data=job.model_dump())


@router.get("/jobs/{job_id}/project")
def get_project(job_id: str) -> ApiResponse:
    repo = JobRepo()
    job = repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    project = detect_maven(Workspace(job.id).repo_dir)
    job.project = project.model_dump()
    repo.save(job)
    return ApiResponse.ok(data=job.project)
