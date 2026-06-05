"""Report + log query API (P1-T10). Read-only."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.common.response import ApiResponse
from app.report.report_assembler import assemble_report
from app.storage.job_repo import JobRepo

router = APIRouter(tags=["report"])


@router.get("/jobs/{job_id}/report")
def get_report(job_id: str) -> ApiResponse:
    job = JobRepo().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return ApiResponse.ok(data=assemble_report(job))


@router.get("/jobs/{job_id}/logs/{stage}", response_class=PlainTextResponse)
def get_log(job_id: str, stage: str) -> str:
    job = JobRepo().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    matches = [s for s in job.stages if s.get("name") == stage and s.get("log_path")]
    if not matches:
        raise HTTPException(status_code=404, detail="log not found for stage")
    path = Path(matches[-1]["log_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="log file missing on disk")
    return path.read_text(encoding="utf-8", errors="replace")
