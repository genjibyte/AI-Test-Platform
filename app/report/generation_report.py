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

from typing import Optional

from app.quality.test_quality_gate import evaluate_test_quality

CONCLUSION = "NEED_HUMAN_REVIEW"  # invariant for all of Phase 2

# GenTestOutcome values that imply the generated test compiled / executed.
_COMPILED = {"PASS", "TEST_FAILURE", "NO_TESTS"}
_EXECUTED = {"PASS", "TEST_FAILURE"}


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


def assemble_generation_report(generation: dict) -> dict:
    target = generation.get("target") or {}
    result = generation.get("result") or {}
    write = generation.get("write") or {}
    execution = generation.get("execution") or {}
    repair = generation.get("repair") or {}
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
    quality = evaluate_test_quality(
        write.get("content") or result.get("test_source") or "",
        execution=execution,
        coverage_delta=coverage,
        production_code_touched=production_code_touched,
        target_class=target.get("target_class") or result.get("target_class"),
        target_method=target.get("target_method") or result.get("target_method"),
        grounding=grounding,
    )

    return {
        "target_class": target.get("target_class") or result.get("target_class"),
        "target_method": target.get("target_method") or result.get("target_method"),
        # generation facts
        "generated": generated,
        "test_class": result.get("test_class_name"),
        "test_file": write.get("file_path"),
        "model": result.get("model"),
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
        "quality_gate": quality.model_dump(),
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
