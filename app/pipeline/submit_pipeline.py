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

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Optional, Sequence

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
from app.report.api_evidence import (
    JUNIT_API_CANDIDATE,
    validate_api_evidence_block,
)
from app.report.api_smoke_manifest import validate_api_smoke_manifest
from app.report.java_test_framework import (
    JavaTestFrameworkFactsValidationError,
    normalize_java_test_framework_declaration,
)
from app.runtime.workspace import Workspace
from app.storage.job_repo import JobRepo
from app.targeting.target_selector import resolve_target

JUNIT_UNIT_CANDIDATE = "junit_unit_candidate"
ALLOWED_SUBMIT_CANDIDATE_KINDS = (JUNIT_UNIT_CANDIDATE, JUNIT_API_CANDIDATE)


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


def _normalize_candidate_kind(candidate_kind: Optional[str]) -> str | None:
    if candidate_kind is None:
        return None
    if not isinstance(candidate_kind, str):
        raise ValueError("candidate_kind must be a string")
    normalized = candidate_kind.strip() or None
    if normalized is None:
        return None
    if normalized not in ALLOWED_SUBMIT_CANDIDATE_KINDS:
        allowed = ", ".join(ALLOWED_SUBMIT_CANDIDATE_KINDS)
        raise ValueError(f"candidate_kind must be one of: {allowed}")
    return normalized


def normalize_submit_candidate_carry(
    *,
    candidate_kind: Optional[str] = None,
    api_evidence: Optional[Mapping[str, Any]] = None,
    api_smoke_manifest: Optional[Mapping[str, Any]] = None,
    java_test_framework: Optional[str] = None,
    target_class: str,
    target_method: Optional[str],
) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Validate optional report-only submit facts and return bundle-safe copies.

    This is not an execution selector. It only protects the submit boundary from
    unsupported candidate kinds, unsafe compact evidence, and manifest/target
    drift before the normal Maven/Surefire judge path runs.
    """
    normalized_kind = _normalize_candidate_kind(candidate_kind)
    try:
        normalized_java_test_framework = normalize_java_test_framework_declaration(
            java_test_framework
        )
    except JavaTestFrameworkFactsValidationError as exc:
        raise ValueError(str(exc)) from exc

    normalized_api_evidence = None
    api_evidence_for_bundle = None
    if api_evidence is not None:
        if normalized_kind != JUNIT_API_CANDIDATE:
            raise ValueError("api_evidence requires candidate_kind=junit_api_candidate")
        if not isinstance(api_evidence, Mapping):
            raise ValueError("api_evidence must be a mapping")
        normalized_api_evidence = validate_api_evidence_block(api_evidence)
        if normalized_api_evidence["candidate_kind"] != JUNIT_API_CANDIDATE:
            raise ValueError(
                "api_evidence.candidate_kind must be junit_api_candidate"
            )
        # Store the caller-supplied compact block, not the validator output that
        # includes report-only conclusion/trusted fields; report assembly
        # normalizes it again as the second defense line.
        api_evidence_for_bundle = deepcopy(dict(api_evidence))

    api_smoke_manifest_for_bundle = None
    if api_smoke_manifest is not None:
        if normalized_kind != JUNIT_API_CANDIDATE:
            raise ValueError(
                "api_smoke_manifest requires candidate_kind=junit_api_candidate"
            )
        if not isinstance(api_smoke_manifest, Mapping):
            raise ValueError("api_smoke_manifest must be a mapping")
        normalized_manifest = validate_api_smoke_manifest(api_smoke_manifest)
        manifest_target = normalized_manifest["target"]
        if manifest_target["target_class"] != target_class:
            raise ValueError(
                "api_smoke_manifest.target.target_class must match target_class"
            )
        manifest_method = manifest_target["target_method"]
        if manifest_method is not None and manifest_method != target_method:
            raise ValueError(
                "api_smoke_manifest.target.target_method must match target_method"
            )
        if normalized_api_evidence is not None:
            evidence_runner = normalized_api_evidence["execution"]["runner_tool"]
            manifest_runner = normalized_manifest["execution_policy"]["runner_tool"]
            if evidence_runner != manifest_runner:
                raise ValueError(
                    "api_evidence.execution.runner_tool must match "
                    "api_smoke_manifest.execution_policy.runner_tool"
                )
        api_smoke_manifest_for_bundle = normalized_manifest

    return (
        normalized_kind,
        api_evidence_for_bundle,
        api_smoke_manifest_for_bundle,
        normalized_java_test_framework,
    )


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
        trusted=False,           # invariant: producer identity is not a quality warrant
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
    candidate_kind: Optional[str] = None,
    api_evidence: Optional[dict] = None,
    api_smoke_manifest: Optional[dict] = None,
    java_test_framework: Optional[str] = None,
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
    (
        normalized_candidate_kind,
        api_evidence_for_bundle,
        api_smoke_manifest_for_bundle,
        java_test_framework_for_bundle,
    ) = normalize_submit_candidate_carry(
        candidate_kind=candidate_kind,
        api_evidence=api_evidence,
        api_smoke_manifest=api_smoke_manifest,
        java_test_framework=java_test_framework,
        target_class=target_class,
        target_method=target_method,
    )
    if normalized_candidate_kind is not None:
        bundle["candidate_kind"] = normalized_candidate_kind
    if api_evidence_for_bundle is not None:
        bundle["api_evidence"] = api_evidence_for_bundle
    if api_smoke_manifest_for_bundle is not None:
        bundle["api_smoke_manifest"] = api_smoke_manifest_for_bundle
    if java_test_framework_for_bundle is not None:
        bundle["java_test_framework"] = java_test_framework_for_bundle

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
