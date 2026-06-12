"""Structural oracle-strength estimate (docs/46 S1).

A deterministic, ADVISORY roll-up of the facts the quality gate already computes
(``app/quality/test_quality_gate.py``) into a single ``oracle_strength`` hint for human
review. It is **STRUCTURAL only** -- it never establishes SEMANTIC strength (whether the
oracle pins the *right* behavior / catches real faults); that stays human review or future
mutation evidence (docs/46 §2/§4). It never accepts/scores a candidate and never changes a
verdict, recommendation, or ``conclusion``.
"""
from __future__ import annotations

from typing import Optional

ORACLE_STRENGTHS = ("none", "weak", "mixed", "structural_ok", "unknown")

# Gate issue codes that determine the structural level (docs/46 §3).
_NONE_CODES = {"no_assertions", "no_test_methods"}
_WEAK_CODES = {"only_weak_assertions", "tautological_assertion"}
_MIXED_CODES = {"weak_assertion_heavy"}
# Advisory caveats that temper a "structural_ok" (noted, but do not lower the level).
_CAVEAT_CODES = {"missing_behavior_sources", "no_obvious_target_reference"}


def estimate_oracle_strength(quality_gate: Optional[dict]) -> dict:
    """Roll up a quality-gate result dict into an advisory STRUCTURAL oracle-strength hint.

    Returns ``{oracle_strength, semantic_strength, reasons, metrics, advisory, note}``.
    Never raises; an unchecked/empty gate -> ``"unknown"``. Pure: no model, no judging,
    no verdict change."""
    q = quality_gate or {}
    m = q.get("metrics") or {}
    metrics = {
        "assertions": m.get("assertions"),
        "weak_assertions": m.get("weak_assertions"),
        "tautological_assertions": m.get("tautological_assertions"),
    }
    if not q.get("checked"):
        return _result("unknown", [], metrics)

    codes = {i.get("code") for i in (q.get("blocking_issues") or [])}
    codes |= {i.get("code") for i in (q.get("warnings") or [])}

    if codes & _NONE_CODES:
        return _result("none", sorted(codes & _NONE_CODES), metrics)
    if codes & _WEAK_CODES:
        return _result("weak", sorted(codes & _WEAK_CODES), metrics)
    if codes & _MIXED_CODES:
        return _result("mixed", sorted(codes & _MIXED_CODES), metrics)
    # Non-weak, non-tautological assertions that passed the structural checks: STRUCTURALLY
    # ok -- but semantic strength is still unknown (carry any caveats for the human).
    return _result("structural_ok", sorted(codes & _CAVEAT_CODES), metrics)


def _result(level: str, reasons: list, metrics: dict) -> dict:
    return {
        "oracle_strength": level,             # STRUCTURAL estimate (docs/46)
        "semantic_strength": "human_review",  # never auto-decided (docs/46 §2)
        "reasons": reasons,
        "metrics": metrics,
        "advisory": True,
        "note": "structural estimate only; not semantic proof (docs/46)",
    }
