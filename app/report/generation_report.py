"""Generation result report assembly (P2-T09).

Pure shaping of a Phase 2 generation *bundle* into a machine-readable report.
Stops at FACTS plus a fixed ``NEED_HUMAN_REVIEW`` conclusion — Phase 2 never
emits accept/reject (that is Phase 4, docs/07 P6). The bundle is the dict the
generate pipeline (P2-T10) persists on the Job; this function never touches I/O.

Bundle shape (all optional; missing pieces degrade gracefully)::

    {
      "target":  {target_class, target_method, file_path, ...},
      "result":  TestGenerationResult.model_dump(),
      "write":   WriteResult.model_dump(),
      "execution": GenExecResult.model_dump(),
      "coverage_delta": CoverageDelta.model_dump(),
      "error":   "<short reason>" | None,
    }
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Optional

from app.quality.asset_sufficiency import estimate_asset_sufficiency
from app.quality.mock_smells import detect_mock_smells
from app.quality.oracle_strength import estimate_oracle_strength
from app.quality.test_level_router import route_test_level
from app.quality.test_quality_gate import evaluate_test_quality
from app.report.api_evidence import (
    ApiEvidenceValidationError,
    JUNIT_API_CANDIDATE,
    validate_api_evidence_block,
)
from app.review.review_digest import build_review_digest
from app.review.review_policy import build_review_summary, recommend_with_reasons

CONCLUSION = "NEED_HUMAN_REVIEW"  # invariant for all of Phase 2
JUNIT_UNIT_CANDIDATE = "junit_unit_candidate"

# GenTestOutcome values that imply the generated test compiled / executed.
_COMPILED = {"PASS", "TEST_FAILURE", "NO_TESTS"}
_EXECUTED = {"PASS", "TEST_FAILURE"}

# Sentinels the model uses to say "no risk / nothing omitted" — these must NOT count
# as a declared risk (otherwise every clean pass would downgrade off STRONG).
_NO_RISK_SENTINELS = {"", "none", "none.", "n/a", "na", "no risk", "no risks"}


def _has_meaningful_risk(items) -> bool:
    """True if the model declared a real risk/omission (ignoring 'none'-style
    sentinels). Drives the conservative STRONG -> REVIEW downgrade (docs/22)."""
    return any(
        str(x).strip().lower().rstrip(".") not in _NO_RISK_SENTINELS
        for x in (items or [])
    )


def _coverage_view(delta: Optional[dict]) -> Optional[dict]:
    if not delta:
        return None
    return {
        "overall_line_delta": delta.get("overall_line_delta"),
        "overall_branch_delta": delta.get("overall_branch_delta"),
        "target_line_delta": delta.get("target_line_delta"),
        "target_branch_delta": delta.get("target_branch_delta"),
        "coverage_dropped": delta.get("coverage_dropped"),
        "target_improved": delta.get("target_improved"),
        "overall_before": delta.get("overall_before"),
        "overall_after": delta.get("overall_after"),
        "target_before": delta.get("target_before"),
        "target_after": delta.get("target_after"),
    }


def _attach_api_evidence_if_present(review_summary: dict, generation: dict) -> None:
    """Attach compact API evidence for the S7A report-only path.

    This is deliberately narrow: it validates a supplied block or creates an empty
    one for ``junit_api_candidate``. It never infers traffic, starts an executor, or
    changes verdicts. Ordinary unit bundles remain unchanged.
    """
    candidate_kind = generation.get("candidate_kind")
    api_evidence = generation.get("api_evidence")

    if candidate_kind is None and api_evidence is None:
        return
    if candidate_kind == JUNIT_UNIT_CANDIDATE and api_evidence is None:
        return
    if candidate_kind not in (None, JUNIT_UNIT_CANDIDATE, JUNIT_API_CANDIDATE):
        raise ApiEvidenceValidationError(
            "S7A report-only wiring supports only junit_unit_candidate "
            "or junit_api_candidate"
        )
    if candidate_kind == JUNIT_UNIT_CANDIDATE and api_evidence is not None:
        raise ApiEvidenceValidationError(
            "api_evidence requires candidate_kind=junit_api_candidate"
        )

    block = {}
    if api_evidence is not None:
        if not isinstance(api_evidence, Mapping):
            raise ApiEvidenceValidationError("api_evidence block must be a mapping")
        block = dict(api_evidence)

    if candidate_kind is not None:
        block_candidate_kind = block.get("candidate_kind")
        if block_candidate_kind not in (None, candidate_kind):
            raise ApiEvidenceValidationError(
                "api_evidence.candidate_kind must match generation.candidate_kind"
            )
        block["candidate_kind"] = candidate_kind
    elif "candidate_kind" not in block:
        block["candidate_kind"] = JUNIT_API_CANDIDATE

    normalized = validate_api_evidence_block(block)
    if normalized["candidate_kind"] != JUNIT_API_CANDIDATE:
        raise ApiEvidenceValidationError(
            "S7A report-only wiring accepts only junit_api_candidate api_evidence"
        )
    review_summary["api_evidence"] = normalized


def assemble_generation_report(generation: dict) -> dict:
    target = generation.get("target") or {}
    result = generation.get("result") or {}
    write = generation.get("write") or {}
    execution = generation.get("execution") or {}
    repair = generation.get("repair") or {}
    preflight = generation.get("preflight") or {}
    delta = generation.get("coverage_delta")

    outcome = execution.get("gen_outcome")
    generated = bool(result.get("test_source"))
    written = bool(write.get("created"))

    coverage = _coverage_view(delta)
    grounding = {
        "used_apis": result.get("used_apis", []),
        "behavior_sources": result.get("behavior_sources", []),
        "omitted_uncertain_cases": result.get("omitted_uncertain_cases", []),
        "risk_flags": result.get("risk_flags", []),
        "dependency_assumptions": result.get("dependency_assumptions", []),
    }
    production_code_touched = bool(write.get("production_code_touched", False))
    test_source = write.get("content") or result.get("test_source") or ""
    target_class = target.get("target_class") or result.get("target_class")
    quality = evaluate_test_quality(
        test_source,
        execution=execution,
        coverage_delta=coverage,
        production_code_touched=production_code_touched,
        target_class=target_class,
        target_method=target.get("target_method") or result.get("target_method"),
        grounding=grounding,
    )

    # Phase 4 review policy (docs/22): advisory triage + reviewer summary.
    # Never changes `conclusion` / `trusted` — the platform still never accepts.
    quality_dict = quality.model_dump()
    # Risk signals already present in the bundle drive a conservative downgrade and
    # explainable reasons: a machine-repaired test, or one the model flagged as
    # risky, is never the top STRONG candidate (docs/22).
    repair_applied = bool(repair.get("repair_rounds", 0))
    model_risk = _has_meaningful_risk(grounding.get("risk_flags")) or (
        _has_meaningful_risk(grounding.get("omitted_uncertain_cases"))
    )
    review_recommendation, review_reasons = recommend_with_reasons(
        quality_status=quality.status,
        gen_outcome=outcome,
        production_code_touched=production_code_touched,
        repair_applied=repair_applied,
        model_risk=model_risk,
    )
    review_summary = build_review_summary(
        generation=generation,
        quality=quality_dict,
        recommendation=review_recommendation,
        recommendation_reasons=review_reasons,
    )
    # docs/46 S1: advisory STRUCTURAL oracle-strength estimate, rolled up from the quality
    # gate. Advisory only -- it does NOT change the recommendation/conclusion set above.
    oracle_strength = estimate_oracle_strength(quality_dict)
    review_summary["oracle_strength_estimate"] = oracle_strength
    # docs/51 #4 S1: advisory mock / external-dependency smells (judge-side). Surfaced for review
    # only -- it does NOT change the recommendation/conclusion and does NOT touch the quality gate.
    mock_smells = detect_mock_smells(test_source, target_class=target_class)
    review_summary["mock_smells"] = mock_smells
    # docs/55 S1: advisory Asset Sufficiency Gate. It uses only report-local facts and is
    # surfaced for review; it does NOT change recommendation/conclusion/trusted.
    review_summary["asset_sufficiency"] = estimate_asset_sufficiency(
        test_source=test_source,
        target_class=target_class,
        target_method=target.get("target_method") or result.get("target_method"),
        quality_gate=quality_dict,
        oracle_strength=oracle_strength,
        mock_smells=mock_smells,
        grounding=grounding,
        preflight=preflight,
        coverage_delta=coverage,
        asset_facts=generation.get("asset_facts"),
    )
    # docs/55 S4A: report-only Test-Level Router. It maps Asset Gate's advisory level to
    # current kernel support, launches no executor, and does not affect digest severity.
    review_summary["test_level_router"] = route_test_level(
        asset_sufficiency=review_summary["asset_sufficiency"],
        run_kind=generation.get("run_kind"),
        producer_id=result.get("producer_id") or generation.get("producer_id"),
    )
    # docs/60_api_candidate/05 S7A: report-only API evidence for the first
    # junit_api_candidate path. This validates compact supplied facts, never starts
    # an executor, and does not feed digest/recommendation/conclusion/trusted.
    _attach_api_evidence_if_present(review_summary, generation)
    # docs/52: advisory review digest -- a prioritized roll-up of the signals above for the
    # reviewer. Built last; reads only what's present; changes no recommendation/conclusion.
    review_summary["digest"] = build_review_digest(review_summary)

    return {
        "target_class": target.get("target_class") or result.get("target_class"),
        "target_method": target.get("target_method") or result.get("target_method"),
        # generation facts
        "generated": generated,
        "test_class": result.get("test_class_name"),
        "test_file": write.get("file_path"),
        "model": result.get("model"),
        # provenance (docs/43 run_kind, docs/53 producer). For a generator run,
        # producer_id is None and run_kind is real/fake/dryrun/smoke; for a
        # submit_candidate run, producer_id names the caller and run_kind="external".
        # Surfaced for the reviewer; NEVER a warrant (trusted stays False).
        "producer_id": result.get("producer_id") or generation.get("producer_id"),
        "run_kind": generation.get("run_kind"),
        "scenarios": result.get("scenarios", []),
        "mocks": result.get("mocks", []),
        # v2 grounding metadata — what the model declared it grounded on / skipped /
        # flagged as risky. Surfaced for the human reviewer (docs/07 P6).
        "grounding": grounding,
        # execution facts
        "gen_outcome": outcome,
        "compiled": outcome in _COMPILED,
        "executed": outcome in _EXECUTED,
        "passed": outcome == "PASS",
        "build_outcome": execution.get("build_outcome"),
        "repair": {
            "enabled": bool(repair.get("enabled", False)),
            "repair_rounds": repair.get("repair_rounds", 0),
            "final_outcome": repair.get("final_outcome"),
            "rounds": repair.get("rounds", []),
        },
        "gen_counts": {
            "total": execution.get("gen_total", 0),
            "passed": execution.get("gen_passed", 0),
            "failed": execution.get("gen_failed", 0),
            "errors": execution.get("gen_errors", 0),
            "skipped": execution.get("gen_skipped", 0),
        },
        # coverage delta (P2-T08)
        "coverage_delta": coverage,
        "quality_gate": quality_dict,
        "preflight": preflight,
        # Phase 4 (docs/22): advisory recommendation + reviewer summary.
        "review_recommendation": review_recommendation,
        "review_summary": review_summary,
        # patch preview: a NEW file, so the full content IS the diff
        "patch": {
            "file_path": write.get("file_path"),
            "is_new_file": written,
            "content": write.get("content"),
        },
        # invariants (docs/07 P2/P6) — never trusted, never touches prod code,
        # never an accept/reject verdict in Phase 2.
        "trusted": bool(result.get("trusted", False)),
        "production_code_touched": production_code_touched,
        "error": generation.get("error"),
        "conclusion": CONCLUSION,
    }
