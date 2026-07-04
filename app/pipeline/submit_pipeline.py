"""submit_candidate pipeline orchestration (docs/53 S1).

Drives ONE external-candidate run on top of a judged (DONE) job. Walks the same
TARGET_SELECT / CONTEXT stages the generator uses, then **skips GENERATE**
(the caller already supplied the test source) and runs SUBMIT_EXECUTE / COMPARE /
SUBMIT_DONE::

    DONE -> TARGET_SELECT -> CONTEXT -> SUBMIT_EXECUTE -> COMPARE -> SUBMIT_DONE
              (any step may short-circuit to SUBMIT_FAILED)

Reuses ``resolve_target`` / ``build_snapshot`` / ``evaluate_generated_test_preflight``
/ ``write_generated_test`` / ``execute_generated_test`` / ``compare`` unchanged.
**No LLM call.** **No production-code edits.** **No oracle rewrite.**
``run_kind`` is hardwired to ``"external"`` (caller cannot override);
``TestGenerationResult.trusted`` stays ``False``; ``conclusion`` stays
``NEED_HUMAN_REVIEW`` -- the judge stack runs unchanged on the assembled bundle.
"""
from __future__ import annotations

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
from app.generate.test_writer import TestWriteError, write_generated_test
from app.llm.run_kind import resolve_run_kind_for_submit
from app.llm.schema import TestGenerationResult
from app.models.job import Job, JobStatus
from app.quality.asset_sufficiency import asset_facts_from_snapshot
from app.quality.generated_test_preflight import evaluate_generated_test_preflight
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


def _submit_fail(repo: JobRepo, job: Job, bundle: dict, reason: str) -> Job:
    """Terminal SUBMIT_FAILED with the partial bundle + reason preserved."""
    bundle["error"] = reason
    job.generation = bundle
    job.status = JobStatus.SUBMIT_FAILED
    job.error = reason
    repo.save(job)
    return repo.get(job.id)


def _preflight_reject_result(generated_class: str) -> GenExecResult:
    """Synthetic execution fact for a deterministic pre-Maven rejection (mirrors
    the generator path so the report assembler handles it identically)."""
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


def _submit_class_name(target_class: str) -> str:
    """Deterministic test class name for an external submit.

    Distinct from the generator path's ``<Simple>AiGeneratedTest`` so the two
    producer paths never collide on disk (docs/53 §1.1, §8).
    """
    simple = target_class.rsplit(".", 1)[-1]
    return f"{simple}SubmittedTest"


def _submit_file_name(target_class: str) -> str:
    return f"{_submit_class_name(target_class)}.java"


def _result_for_submit(
    target_class: str,
    target_method: Optional[str],
    package: Optional[str],
    test_source: str,
    producer_id: str,
) -> TestGenerationResult:
    """Construct a platform-controlled ``TestGenerationResult`` for an external
    candidate. Identity (target/class name/file/trusted) is set by US, never by
    the caller (docs/53 §2.1). ``trusted`` stays ``False`` -- producer_id is a
    manifest, not a warrant."""
    return TestGenerationResult(
        target_class=target_class,
        target_method=target_method,
        package=package,
        test_class_name=_submit_class_name(target_class),
        file_name=_submit_file_name(target_class),
        imports=[],
        test_source=test_source,
        scenarios=[],
        mocks=[],
        notes=None,
        model=producer_id,       # surfaces in headline/group_by analytics
        trusted=False,           # invariant, docs/07 P2 + docs/53 §4
        producer_id=producer_id, # docs/53
    )


def run_external_candidate(
    job: Job,
    repo: JobRepo,
    target_class: str,
    target_method: Optional[str],
    test_source: str,
    producer_id: str,
    *,
    producer_meta: Optional[dict] = None,
    maven_extra_args: Optional[Sequence[str]] = None,
) -> Job:
    """Run the submit_candidate pipeline on a judged job (docs/53 S1).

    The caller-supplied ``test_source`` is treated as the candidate; the platform
    derives identity, runs preflight + execute + compare, and assembles the same
    bundle shape the generator path produces. The judge stack
    (``assemble_generation_report``) consumes the bundle unchanged.
    """
    bundle = _empty_bundle()
    # run_kind is hardwired here; the caller never supplies one (no parameter).
    bundle["run_kind"] = resolve_run_kind_for_submit()
    bundle["producer_id"] = producer_id
    bundle["producer_meta"] = dict(producer_meta or {})

    if job.status != JobStatus.DONE:
        return _submit_fail(
            repo, job, bundle,
            f"submit_candidate requires a judged job (status={job.status.value})",
        )
    workspace = Workspace(job.id)
    repo_dir = workspace.repo_dir
    if not repo_dir.is_dir():
        return _submit_fail(repo, job, bundle, "job workspace missing; re-import required")

    # --- TARGET_SELECT ----------------------------------------------------
    repo.update_status(job.id, JobStatus.TARGET_SELECT)
    job = repo.get(job.id)
    target, structure = resolve_target(repo_dir, target_class, target_method)
    job.target = target.model_dump()
    bundle["target"] = job.target
    repo.save(job)
    if not target.exists or structure is None:
        return _submit_fail(repo, job, bundle, target.reason or "target class not found")
    if target_method is not None and target.method_exists is False:
        return _submit_fail(
            repo, job, bundle, f"target method '{target_method}' not found",
        )

    # --- CONTEXT ----------------------------------------------------------
    repo.update_status(job.id, JobStatus.CONTEXT)
    job = repo.get(job.id)
    try:
        snapshot = build_snapshot(repo_dir, target_class, target_method)
    except ContextError as exc:
        return _submit_fail(repo, job, bundle, f"context collection failed: {exc}")
    # docs/55 S2: persist tiny asset facts from the bounded context; never the full snapshot.
    bundle["asset_facts"] = asset_facts_from_snapshot(snapshot)

    # baseline coverage BEFORE the submitted test runs.
    baseline_overall = parse_jacoco(repo_dir)
    baseline_target = parse_jacoco_class(repo_dir, target_class)

    # --- SUBMIT_EXECUTE ---------------------------------------------------
    # Build the platform-controlled result, then preflight / write / execute.
    # No LLM call (docs/53 §4); identity is ours, content is the caller's.
    result = _result_for_submit(
        target_class=target_class,
        target_method=target_method,
        package=structure.package,
        test_source=test_source,
        producer_id=producer_id,
    )
    bundle["result"] = result.model_dump()

    preflight = evaluate_generated_test_preflight(result.test_source, snapshot)
    bundle["preflight"] = preflight.model_dump()
    job.generation = bundle
    repo.save(job)
    if preflight.status == "FAIL":
        repo.update_status(job.id, JobStatus.SUBMIT_EXECUTE)
        job = repo.get(job.id)
        bundle["execution"] = _preflight_reject_result(fqcn_of(result)).model_dump()
        job.generation = bundle
        repo.save(job)
        repo.update_status(job.id, JobStatus.COMPARE)
        job = repo.get(job.id)
        job.generation = bundle
        repo.save(job)
        repo.update_status(job.id, JobStatus.SUBMIT_DONE)
        return repo.get(job.id)

    try:
        write = write_generated_test(repo_dir, result)
    except TestWriteError as exc:
        return _submit_fail(repo, job, bundle, f"write failed: {exc}")
    bundle["write"] = write.model_dump()
    job.generation = bundle
    repo.save(job)

    repo.update_status(job.id, JobStatus.SUBMIT_EXECUTE)
    job = repo.get(job.id)
    exec_result = execute_generated_test(
        repo_dir, workspace, fqcn_of(result), maven_extra_args=maven_extra_args,
    )
    bundle["execution"] = exec_result.model_dump()
    job.generation = bundle
    repo.save(job)
    if exec_result.gen_outcome == GenTestOutcome.NO_MAVEN:
        return _submit_fail(repo, job, bundle, "maven not available (set TESTAGENT_MAVEN_CMD)")

    # --- COMPARE (baseline vs after) --------------------------------------
    repo.update_status(job.id, JobStatus.COMPARE)
    job = repo.get(job.id)
    after_overall = parse_jacoco(repo_dir)
    after_target = parse_jacoco_class(repo_dir, target_class)
    delta = compare(
        baseline_overall, after_overall, baseline_target, after_target, target_class,
    )
    bundle["coverage_delta"] = delta.model_dump()
    job.generation = bundle
    repo.save(job)

    repo.update_status(job.id, JobStatus.SUBMIT_DONE)
    return repo.get(job.id)
