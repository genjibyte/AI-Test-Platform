"""Phase 4 review policy (docs/22).

Turns existing generation facts into (a) a deterministic, ADVISORY review
recommendation and (b) an actionable reviewer summary. It NEVER auto-accepts
(the platform ``conclusion`` stays ``NEED_HUMAN_REVIEW``), NEVER calls a model,
and NEVER edits the generated test. It does not repair oracles — a TEST_FAILURE
is surfaced for human judgement, not auto-fixed.
"""
from __future__ import annotations

import re

# Recommendation taxonomy — an advisory ordering for the reviewer, NOT a verdict.
REJECT_CANDIDATE = "REJECT_CANDIDATE"
NEEDS_REVISION = "NEEDS_REVISION"
REVIEW_CANDIDATE = "REVIEW_CANDIDATE"
STRONG_REVIEW_CANDIDATE = "STRONG_REVIEW_CANDIDATE"
RECOMMENDATIONS = (
    REJECT_CANDIDATE,
    NEEDS_REVISION,
    REVIEW_CANDIDATE,
    STRONG_REVIEW_CANDIDATE,
)

# The platform never auto-accepts; this is invariant (docs/07 P6).
CONCLUSION = "NEED_HUMAN_REVIEW"

# JUnit5 "expected: <X> but was: <Y>" (covers assertEquals and the
# assertThrows "Unexpected exception type thrown, expected: <..> but was: <..>").
_EXP_ACT_RE = re.compile(
    r"expected:\s*<(?P<exp>.*?)>\s*but was:\s*<(?P<act>.*?)>", re.DOTALL
)
_MSG_LIMIT = 500


def recommend(
    *,
    quality_status: str | None,
    gen_outcome: str | None,
    production_code_touched: bool,
) -> str:
    """Deterministic advisory triage (docs/22 §2). Conservative on uncertainty."""
    if production_code_touched:                       # red-line guard
        return REJECT_CANDIDATE
    if quality_status == "FAIL":                      # structural defect / not executed
        return REJECT_CANDIDATE
    if gen_outcome == "TEST_FAILURE":                 # oracle vs bug — human decides
        return NEEDS_REVISION
    if quality_status == "REVIEW":                    # warnings, but reviewable
        return REVIEW_CANDIDATE
    if quality_status == "PASS" and gen_outcome == "PASS":
        return STRONG_REVIEW_CANDIDATE                # strongest candidate — still reviewed
    return REVIEW_CANDIDATE                           # conservative fallback


def _expected_actual(message: str) -> tuple[str | None, str | None]:
    m = _EXP_ACT_RE.search(message or "")
    if m:
        return m.group("exp"), m.group("act")
    return None, None


def _failure_views(execution: dict) -> list[dict]:
    """Only the GENERATED test's own failed cases, with expected/actual when present."""
    fqcn = execution.get("generated_class")
    suite = execution.get("suite_result") or {}
    views: list[dict] = []
    for case in suite.get("failed_cases") or []:
        if case.get("classname") != fqcn:
            continue
        message = (case.get("message") or "")[:_MSG_LIMIT]
        expected, actual = _expected_actual(message)
        if expected is None and actual is None:
            # not an assertion diff (e.g. an exception): the message is the actual.
            actual = message or None
        views.append(
            {
                "test_name": case.get("name"),
                "type": case.get("type"),       # "failure" (assert) | "error" (exception)
                "expected": expected,
                "actual": actual,
                "raw_message": message or None,
            }
        )
    return views


def build_review_summary(
    *, generation: dict, quality: dict, recommendation: str
) -> dict:
    """Assemble an actionable reviewer summary from existing facts only."""
    execution = generation.get("execution") or {}
    result = generation.get("result") or {}
    write = generation.get("write") or {}
    target = generation.get("target") or {}
    preflight = generation.get("preflight") or {}
    return {
        "recommendation": recommendation,
        "conclusion": CONCLUSION,
        "target": {
            "target_class": target.get("target_class") or result.get("target_class"),
            "target_method": target.get("target_method") or result.get("target_method"),
        },
        "outcome": execution.get("gen_outcome"),
        "quality": {
            "status": quality.get("status"),
            "blockers": [i.get("code") for i in quality.get("blocking_issues") or []],
            "warnings": [i.get("code") for i in quality.get("warnings") or []],
            "advisories": [i.get("code") for i in quality.get("advisories") or []],
        },
        "failures": _failure_views(execution),
        "grounding": {
            "behavior_sources": result.get("behavior_sources", []),
            "omitted_uncertain_cases": result.get("omitted_uncertain_cases", []),
            "risk_flags": result.get("risk_flags", []),
            "dependency_assumptions": result.get("dependency_assumptions", []),
        },
        "preflight": {
            "status": preflight.get("status"),
            "blockers": [
                {
                    "code": i.get("code"),
                    "evidence": i.get("evidence"),
                }
                for i in preflight.get("blocking_issues") or []
            ],
        },
        "patch_preview": {
            "file_path": write.get("file_path"),
            "is_new_file": bool(write.get("created")),
        },
        "invariants": {
            "trusted": bool(result.get("trusted", False)),
            "production_code_touched": bool(write.get("production_code_touched", False)),
        },
    }
