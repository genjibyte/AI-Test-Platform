"""Phase 2 generation pipeline orchestration (P2-T10).

Drives ONE generation run on top of a judged (DONE) job, advancing the Phase 2
state machine::

    DONE -> TARGET_SELECT -> CONTEXT -> GENERATE -> GEN_EXECUTE -> COMPARE -> GEN_DONE
              (any step may short-circuit to GEN_FAILED)

Distinction (docs/07 A4 — never hide failures):

- A generated test that compiles & runs but FAILS, or fails to compile, is a
  recorded *result*. The pipeline still reaches GEN_DONE and the report carries
  the facts + ``NEED_HUMAN_REVIEW``. We do not pretend it passed, nor do we drop
  the run on the floor.
- Only infrastructure / precondition problems (job not judged, workspace gone,
  target/context/write errors, Maven unavailable) short-circuit to GEN_FAILED.

Phase 2 red-lines honored: no production-code edits, no auto-commit, and no
auto-accept. Later opt-in compile repair and deterministic quality checks are
surfaced as review metadata.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from app.context.context_collector import ContextError, build_snapshot
from app.coverage.coverage_compare import compare
from app.coverage.jacoco_parser import parse_jacoco, parse_jacoco_class
from app.generate.gen_executor import (
    GenExecResult,
    GenTestOutcome,
    execute_generated_test,
    fqcn_of,
)
from app.generate.generation import dry_generate
from app.generate.test_writer import TestWriteError, write_generated_test
from app.llm.client import LLMClient, LLMRequestError, get_client
from app.llm.schema import LLMOutputError
from app.models.job import Job, JobStatus
from app.quality.generated_test_preflight import evaluate_generated_test_preflight
from app.repair.compile_repair import repair_compile_failure
from app.runtime.workspace import Workspace
from app.storage.job_repo import JobRepo
from app.targeting.target_selector import resolve_target


def _empty_bundle() -> dict:
    return {
        "target": None,
        "result": None,
        "write": None,
        "execution": None,
        "coverage_delta": None,
        "error": None,
    }


def _gen_fail(repo: JobRepo, job: Job, bundle: dict, reason: str) -> Job:
    """Terminal GEN_FAILED with the partial bundle + reason preserved."""
    bundle["error"] = reason
    job.generation = bundle
    job.status = JobStatus.GEN_FAILED  # direct set: short-circuit from any step
    job.error = reason
    repo.save(job)
    return repo.get(job.id)


def _preflight_reject_result(generated_class: str) -> GenExecResult:
    """Synthetic execution fact for a deterministic pre-Maven rejection."""
    return GenExecResult(
        generated_class=generated_class,
        gen_outcome=GenTestOutcome.COMPILE_FAILURE,
        build_outcome="PREFLIGHT_REJECT",
        gen_report_found=False,
        gen_total=0,
        gen_passed=0,
        gen_failed=0,
        gen_errors=0,
        gen_skipped=0,
        suite_result={},
        after_coverage={"has_report": False},
        log_path=None,
        exec_record={
            "tool": "generated_test_preflight",
            "outcome": "PREFLIGHT_REJECT",
        },
    )


def run_generation(
    job: Job,
    repo: JobRepo,
    target_class: str,
    target_method: Optional[str] = None,
    client: Optional[LLMClient] = None,
    maven_extra_args: Optional[Sequence[str]] = None,
    repair_compile_failures: bool = False,
    max_repair_rounds: int = 1,
) -> Job:
    bundle = _empty_bundle()

    if job.status != JobStatus.DONE:
        return _gen_fail(
            repo, job, bundle,
            f"generation requires a judged job (status={job.status.value})",
        )
    workspace = Workspace(job.id)
    repo_dir = workspace.repo_dir
    if not repo_dir.is_dir():
        return _gen_fail(repo, job, bundle, "job workspace missing; re-import required")

    # --- TARGET_SELECT ----------------------------------------------------
    repo.update_status(job.id, JobStatus.TARGET_SELECT)
    job = repo.get(job.id)
    target, structure = resolve_target(repo_dir, target_class, target_method)
    job.target = target.model_dump()
    bundle["target"] = job.target
    repo.save(job)
    if not target.exists or structure is None:
        return _gen_fail(repo, job, bundle, target.reason or "target class not found")
    if target_method is not None and target.method_exists is False:
        return _gen_fail(
            repo, job, bundle, f"target method '{target_method}' not found"
        )

    # --- CONTEXT ----------------------------------------------------------
    repo.update_status(job.id, JobStatus.CONTEXT)
    job = repo.get(job.id)
    try:
        snapshot = build_snapshot(repo_dir, target_class, target_method)
    except ContextError as exc:
        return _gen_fail(repo, job, bundle, f"context collection failed: {exc}")

    # Capture the baseline coverage BEFORE the generated test runs — at this
    # point the workspace still holds the Phase 1 jacoco.xml.
    baseline_overall = parse_jacoco(repo_dir)
    baseline_target = parse_jacoco_class(repo_dir, target_class)

    # --- GENERATE (LLM -> artifact -> independent test file) --------------
    repo.update_status(job.id, JobStatus.GENERATE)
    job = repo.get(job.id)
    try:
        result = dry_generate(snapshot, client or get_client())
    except LLMRequestError as exc:  # auth / quota / network / bad model name
        return _gen_fail(repo, job, bundle, f"LLM request failed: {exc}")
    except LLMOutputError as exc:   # model returned unparseable / off-schema JSON
        return _gen_fail(repo, job, bundle, f"LLM output invalid: {exc}")
    bundle["result"] = result.model_dump()

    preflight = evaluate_generated_test_preflight(result.test_source, snapshot)
    bundle["preflight"] = preflight.model_dump()
    job.generation = bundle
    repo.save(job)
    if preflight.status == "FAIL":
        repo.update_status(job.id, JobStatus.GEN_EXECUTE)
        job = repo.get(job.id)
        bundle["execution"] = _preflight_reject_result(
            fqcn_of(result)
        ).model_dump()
        job.generation = bundle
        repo.save(job)
        repo.update_status(job.id, JobStatus.COMPARE)
        job = repo.get(job.id)
        job.generation = bundle
        repo.save(job)
        repo.update_status(job.id, JobStatus.GEN_DONE)
        return repo.get(job.id)

    try:
        write = write_generated_test(repo_dir, result)
    except TestWriteError as exc:
        return _gen_fail(repo, job, bundle, f"write failed: {exc}")
    bundle["write"] = write.model_dump()
    job.generation = bundle
    repo.save(job)

    # --- GEN_EXECUTE (reuse Phase 1 runner) -------------------------------
    repo.update_status(job.id, JobStatus.GEN_EXECUTE)
    job = repo.get(job.id)
    exec_result = execute_generated_test(
        repo_dir, workspace, fqcn_of(result), maven_extra_args=maven_extra_args
    )
    bundle["execution"] = exec_result.model_dump()
    job.generation = bundle
    repo.save(job)
    if exec_result.gen_outcome == GenTestOutcome.NO_MAVEN:
        return _gen_fail(repo, job, bundle, "maven not available (set TESTAGENT_MAVEN_CMD)")

    if repair_compile_failures and exec_result.gen_outcome == GenTestOutcome.COMPILE_FAILURE:
        attempts = []
        test_path = repo_dir / write.file_path
        for round_no in range(1, max(0, max_repair_rounds) + 1):
            try:
                source = test_path.read_text(encoding="utf-8")
            except OSError as exc:
                attempts.append({
                    "round": round_no,
                    "changed": False,
                    "error": f"read generated test failed: {exc}",
                })
                break
            log_text = ""
            if exec_result.log_path:
                try:
                    log_text = Path(exec_result.log_path).read_text(
                        encoding="utf-8", errors="replace"
                    )
                except OSError:
                    log_text = ""
            repair = repair_compile_failure(
                source,
                log_text,
                java_source_level=snapshot.build_constraints.java_source,
            )
            attempt = {
                "round": round_no,
                "changed": repair.changed,
                "patches": [p.model_dump() for p in repair.patches],
                "before_outcome": exec_result.gen_outcome.value,
            }
            attempts.append(attempt)
            if not repair.changed:
                break

            test_path.write_text(repair.source, encoding="utf-8")
            write.content = repair.source
            bundle["write"] = write.model_dump()
            exec_result = execute_generated_test(
                repo_dir, workspace, fqcn_of(result), maven_extra_args=maven_extra_args
            )
            attempt["after_outcome"] = exec_result.gen_outcome.value
            bundle["execution"] = exec_result.model_dump()
            bundle["repair"] = {
                "enabled": True,
                "rounds": attempts,
                "repair_rounds": len([a for a in attempts if a.get("changed")]),
                "final_outcome": exec_result.gen_outcome.value,
            }
            job.generation = bundle
            repo.save(job)
            if exec_result.gen_outcome != GenTestOutcome.COMPILE_FAILURE:
                break

        if attempts and "repair" not in bundle:
            bundle["repair"] = {
                "enabled": True,
                "rounds": attempts,
                "repair_rounds": len([a for a in attempts if a.get("changed")]),
                "final_outcome": exec_result.gen_outcome.value,
            }
            job.generation = bundle
            repo.save(job)

    # --- COMPARE (baseline vs after) --------------------------------------
    repo.update_status(job.id, JobStatus.COMPARE)
    job = repo.get(job.id)
    after_overall = parse_jacoco(repo_dir)
    after_target = parse_jacoco_class(repo_dir, target_class)
    delta = compare(
        baseline_overall, after_overall, baseline_target, after_target, target_class
    )
    bundle["coverage_delta"] = delta.model_dump()
    job.generation = bundle
    repo.save(job)

    # GEN_DONE = "generation pipeline completed", NOT "test passed". The report
    # carries compile/exec/coverage facts and NEED_HUMAN_REVIEW.
    repo.update_status(job.id, JobStatus.GEN_DONE)
    return repo.get(job.id)
