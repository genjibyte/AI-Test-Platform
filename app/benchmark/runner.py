"""Benchmark runner (Phase 2.5).

For each (repo, target) case: judge the repo (Phase 1) then generate one test
(Phase 2), each in an isolated per-job workspace, and record the facts. Repos
are shallow-cloned ONCE into a local mirror so repeated targets on the same repo
don't re-hit the network. Re-uses the existing pipelines verbatim — no new
judging logic.

Isolation: the workspace root is pointed at ``workdir/ws`` via the standard
TESTAGENT_WORKSPACE_ROOT setting (cache cleared once), so every job lands under
a unique ``<root>/<job_id>/`` directory. The LLM client is whatever is
configured (offline fake by default).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from app.benchmark.models import (
    COVERAGE_AVAILABLE,
    COVERAGE_UNAVAILABLE,
    BenchCase,
    BenchCaseResult,
    BenchReport,
    aggregate,
    classify_failure,
)
from app.config import get_settings
from app.llm.client import LLMClient, get_client
from app.models.job import Job, JobStatus, now_iso
from app.pipeline.generate_pipeline import run_generation
from app.pipeline.judge_pipeline import run_pipeline
from app.report.generation_report import assemble_generation_report
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo


def _git(*args: str) -> None:
    subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, timeout=600
    )


def _ensure_mirror(
    repo_url: str,
    branch: Optional[str],
    cache_dir: Path,
    commit: Optional[str] = None,
) -> str:
    """Shallow-clone the repo once; return a file:// URI for fast local re-clone.

    When ``commit`` is given (frozen manifest), pin to that exact SHA via an
    init + shallow fetch-by-SHA, then put HEAD on a local ``pinned`` branch so a
    downstream ``git clone`` of the mirror checks out exactly that revision.
    Otherwise shallow-clone the (optional) branch tip as before. ``commit`` is
    part of the cache key, so different pins on one repo get distinct mirrors.
    """
    key = hashlib.sha1(
        f"{repo_url}@{branch or ''}@{commit or ''}".encode()
    ).hexdigest()[:16]
    dest = cache_dir / key
    if not (dest / ".git").is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if commit:
            dest.mkdir(parents=True, exist_ok=True)
            _git("init", "-q", str(dest))
            _git("-C", str(dest), "fetch", "--depth", "1", repo_url, commit)
            _git("-C", str(dest), "checkout", "-q", "-b", "pinned", "FETCH_HEAD")
        else:
            args = ["clone", "--depth", "1"]
            if branch:
                args += ["--branch", branch]
            args += [repo_url, str(dest)]
            _git(*args)
    return dest.as_uri()


def _tail(path: Optional[str], limit: int = 12000) -> str:
    """Best-effort tail of a build log for log-aware failure classification."""
    if not path:
        return ""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:]


def _case_failure(
    case: BenchCase,
    t0: float,
    failure_type: str,
    error: str,
) -> BenchCaseResult:
    """Record a case-level setup failure before a job can be judged."""
    return BenchCaseResult(
        name=case.label(),
        repo_url=case.repo_url,
        branch=case.branch,
        target_class=case.target_class,
        target_method=case.target_method,
        repo_judged=False,
        generation_status=failure_type,
        failure_type=failure_type,
        coverage_status=COVERAGE_UNAVAILABLE,
        runtime_ms=int((time.monotonic() - t0) * 1000),
        error=error,
    )


def _baseline_result(case: BenchCase, job: Job, t0: float) -> BenchCaseResult:
    """Repo failed to judge — record the baseline failure, no generation."""
    return BenchCaseResult(
        name=case.label(),
        repo_url=case.repo_url,
        branch=case.branch,
        commit_hash=job.commit_sha,
        target_class=case.target_class,
        target_method=case.target_method,
        repo_judged=False,
        baseline_build_outcome=job.build_outcome,
        generation_status="REPO_NOT_BUILDABLE",
        failure_type="REPO_NOT_BUILDABLE",
        coverage_status=COVERAGE_UNAVAILABLE,
        runtime_ms=int((time.monotonic() - t0) * 1000),
        error=job.error,
    )


def _completed_result(case: BenchCase, job: Job, t0: float) -> BenchCaseResult:
    rep = assemble_generation_report(job.generation or {})
    cov = job.coverage or {}
    tests = job.test_result or {}
    cd = rep.get("coverage_delta") or {}
    repair = rep.get("repair") or {}
    quality = rep.get("quality_gate") or {}
    status = job.status.value
    execution = (job.generation or {}).get("execution") or {}
    log_text = _tail(execution.get("log_path"))
    tests_green = (
        bool(tests.get("has_reports"))
        and tests.get("failed", 0) == 0
        and tests.get("errors", 0) == 0
    ) if tests else None

    # Coverage is "available" only when BOTH before and after JaCoCo reports
    # exist; otherwise (skipped to avoid F2, or absent) it is unavailable and we
    # null the deltas rather than report a misleading 0.0.
    after_ok = bool((cd.get("overall_after") or {}).get("has_report"))
    before_ok = bool((cd.get("overall_before") or {}).get("has_report"))
    cov_available = after_ok and before_ok
    cov_status = COVERAGE_AVAILABLE if cov_available else COVERAGE_UNAVAILABLE

    return BenchCaseResult(
        name=case.label(),
        repo_url=case.repo_url,
        branch=case.branch,
        commit_hash=job.commit_sha,
        target_class=case.target_class,
        target_method=case.target_method,
        repo_judged=True,
        baseline_build_outcome=job.build_outcome,
        baseline_tests_green=tests_green,
        baseline_line_rate=cov.get("line_rate") if cov.get("has_report") else None,
        baseline_branch_rate=cov.get("branch_rate") if cov.get("has_report") else None,
        generation_status=status,
        gen_outcome=rep.get("gen_outcome"),
        compiled=rep.get("compiled"),
        executed=rep.get("executed"),
        passed=rep.get("passed"),
        target_line_delta=cd.get("target_line_delta") if cov_available else None,
        target_branch_delta=cd.get("target_branch_delta") if cov_available else None,
        coverage_dropped=cd.get("coverage_dropped") if cov_available else None,
        target_improved=cd.get("target_improved") if cov_available else None,
        failure_type=classify_failure(
            True, status, rep.get("gen_outcome"), log_text
        ),
        coverage_status=cov_status,
        production_code_touched=rep.get("production_code_touched"),
        model=rep.get("model"),
        conclusion=rep.get("conclusion"),
        repair_rounds=repair.get("repair_rounds") if repair.get("enabled") else None,
        repair_final_outcome=repair.get("final_outcome"),
        quality_gate_status=quality.get("status"),
        quality_blockers=len(quality.get("blocking_issues") or []),
        quality_warnings=len(quality.get("warnings") or []),
        review_recommendation=rep.get("review_recommendation"),
        review_summary=rep.get("review_summary"),
        runtime_ms=int((time.monotonic() - t0) * 1000),
        error=(job.generation or {}).get("error"),
    )


def run_case(
    case: BenchCase,
    repo_db: JobRepo,
    client: LLMClient,
    mirror_uri: str,
    maven_extra_args: Optional[list[str]] = None,
) -> BenchCaseResult:
    """Judge the repo, then (if buildable) generate one test for the target."""
    t0 = time.monotonic()
    job = Job(git_url=mirror_uri, branch=case.branch)
    repo_db.create(job)
    job = run_pipeline(
        job, repo_db, maven_extra_args=maven_extra_args
    )  # Phase 1 judge (import + build + parse)
    if job.status != JobStatus.DONE:
        return _baseline_result(case, job, t0)
    job = run_generation(
        job,
        repo_db,
        case.target_class,
        case.target_method,
        client=client,
        maven_extra_args=maven_extra_args,
        repair_compile_failures=get_settings().repair_compile_failures,
        max_repair_rounds=get_settings().repair_max_rounds,
    )
    return _completed_result(case, job, t0)


def run_benchmark(
    cases: List[BenchCase],
    workdir: Path,
    client: Optional[LLMClient] = None,
) -> BenchReport:
    workdir = Path(workdir).resolve()  # absolute: required for file:// mirror URIs
    workdir.mkdir(parents=True, exist_ok=True)

    # Point every job's workspace under workdir/ws via the standard setting.
    os.environ["TESTAGENT_WORKSPACE_ROOT"] = str(workdir / "ws")
    get_settings.cache_clear()
    settings = get_settings()

    try:
        client = client or get_client(settings)
    except Exception as exc:  # noqa: BLE001 - benchmark should produce a report
        results = [
            _case_failure(c, time.monotonic(), "LLM_CONFIG_FAILED", str(exc))
            for c in cases
        ]
        return BenchReport(
            provider=settings.llm_provider,
            model=settings.llm_model,
            generated_at=now_iso(),
            maven=settings.maven_cmd,
            cases=results,
            aggregate=aggregate(results),
        )

    maven_extra_args = settings.mvn_extra_args.split() if settings.mvn_extra_args else []
    db = workdir / "bench.db"
    init_db(db)
    repo_db = JobRepo(conn=get_connection(db))

    mirrors: dict[tuple, str] = {}
    results: List[BenchCaseResult] = []
    for case in cases:
        mkey = (case.repo_url, case.branch, case.commit)
        if mkey not in mirrors:
            try:
                mirrors[mkey] = _ensure_mirror(
                    case.repo_url, case.branch, workdir / "mirrors", commit=case.commit
                )
            except (subprocess.SubprocessError, OSError) as exc:
                results.append(
                    _case_failure(case, time.monotonic(), "REPO_CLONE_FAILED", str(exc))
                )
                continue
        results.append(
            run_case(case, repo_db, client, mirrors[mkey], maven_extra_args)
        )

    model = next((r.model for r in results if r.model), settings.llm_model)
    return BenchReport(
        provider=settings.llm_provider,
        model=model,
        generated_at=now_iso(),
        maven=settings.maven_cmd,
        cases=results,
        aggregate=aggregate(results),
    )
