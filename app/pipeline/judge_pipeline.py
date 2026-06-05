"""Judge pipeline orchestration (P1-T09).

Drives one job through the Phase 1 judging flow, advancing the state machine::

    IMPORTING -> BUILDING -> PARSING -> DONE
       (any stage may short-circuit to FAILED)

DONE means "judging completed" — not "tests passed". A run whose original tests
fail (TEST_FAILURE) still reaches DONE; the report carries the verdict. Only
import / non-maven / compile / build / no-maven problems fail the run.

No LLM, no generation, no fixer — Phase 1 is read-only judging.
"""
from __future__ import annotations

from app.build.maven_runner import BuildOutcome
from app.coverage.jacoco_parser import parse_jacoco
from app.coverage.jacoco_runner import run_mvn_test_with_coverage
from app.detect.maven_detector import detect
from app.importer.git_importer import import_repo
from app.models.job import Job, JobStatus
from app.report.surefire_parser import parse_surefire
from app.runtime.workspace import Workspace
from app.storage.job_repo import JobRepo


def _fail(repo: JobRepo, job: Job, reason: str) -> Job:
    job.status = JobStatus.FAILED
    job.error = reason
    repo.save(job)
    return job


def run_pipeline(job: Job, repo: JobRepo) -> Job:
    workspace = Workspace(job.id)

    # --- IMPORT -----------------------------------------------------------
    repo.update_status(job.id, JobStatus.IMPORTING)
    record, commit = import_repo(job.git_url, workspace, branch=job.branch)
    job = repo.get(job.id)
    job.stages.append(record.trimmed())
    if not record.success:
        return _fail(repo, job, "git import failed (see import.log)")
    job.commit_sha = commit
    repo.save(job)

    # --- BUILD (detect + mvn test with coverage) --------------------------
    repo.update_status(job.id, JobStatus.BUILDING)
    job = repo.get(job.id)
    project = detect(workspace.repo_dir)
    job.project = project.model_dump()
    repo.save(job)
    if not project.is_maven:
        return _fail(repo, job, f"not a maven project: {project.reason}")

    build_record, outcome = run_mvn_test_with_coverage(workspace.repo_dir, workspace)
    job = repo.get(job.id)
    job.build_outcome = outcome.value
    if build_record is not None:
        job.stages.append(build_record.trimmed())
    repo.save(job)

    if outcome == BuildOutcome.NO_MAVEN:
        return _fail(repo, job, "maven not available (set TESTAGENT_MAVEN_CMD)")
    if outcome in (BuildOutcome.COMPILE_FAILURE, BuildOutcome.BUILD_ERROR):
        return _fail(repo, job, f"build failed: {outcome.value}")

    # --- PARSE (surefire + jacoco) ----------------------------------------
    repo.update_status(job.id, JobStatus.PARSING)
    job = repo.get(job.id)
    job.test_result = parse_surefire(workspace.repo_dir).model_dump()
    job.coverage = parse_jacoco(workspace.repo_dir).summary()
    repo.save(job)

    repo.update_status(job.id, JobStatus.DONE)
    return repo.get(job.id)
