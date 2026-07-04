"""Review digest (docs/52) -- an ADVISORY roll-up of the per-candidate review signals into one
prioritized human-review checklist. It READS signals already on ``review_summary``
(oracle-strength, mutation survivors, invariant verification, mock smells, asset sufficiency,
the quality gate) and emits ordered flags + a headline. It computes NOTHING new and changes NO
verdict: it never feeds ``recommend_with_reasons``/``conclusion``; ``auto_accept_blocked`` stays
True; ``conclusion`` stays ``NEED_HUMAN_REVIEW``. A flag is a place to look, not a rejection.
"""
from __future__ import annotations

from typing import List

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def _flag(flags: List[dict], signal: str, severity: str, message: str) -> None:
    flags.append({"signal": signal, "severity": severity, "message": message})


def build_review_digest(review_summary: dict) -> dict:
    """Roll up the advisory signals present on ``review_summary`` into a prioritized digest.
    Pure; never raises; reads only what is present (signals are attached at different layers)."""
    rs = review_summary or {}
    flags: List[dict] = []

    # quality gate (the gate's own blockers -- surfaced, not recomputed)
    q = rs.get("quality") or {}
    if q.get("blockers"):
        _flag(flags, "quality_gate", "high",
              f"quality-gate blockers: {', '.join(q['blockers'])}")

    # oracle strength (docs/46)
    oracle = (rs.get("oracle_strength_estimate") or {}).get("oracle_strength")
    if oracle == "none":
        _flag(flags, "oracle_strength", "high", "no real assertions (oracle: none)")
    elif oracle == "weak":
        _flag(flags, "oracle_strength", "high", "only weak assertions (oracle: weak)")
    elif oracle == "mixed":
        _flag(flags, "oracle_strength", "medium", "many weak assertions (oracle: mixed)")

    # mock / external-dependency smells (docs/51)
    mc = (rs.get("mock_smells") or {}).get("counts") or {}
    if mc.get("mock_of_target"):
        _flag(flags, "mock_smells", "high", "mocks the class under test (tests the mock)")
    if mc.get("real_dependency"):
        _flag(flags, "mock_smells", "medium", "uses a real framework dependency in a unit test")
    if mc.get("stub_returns_null"):
        _flag(flags, "mock_smells", "low", "stubs return null (may mask null handling)")
    if mc.get("loose_matchers"):
        _flag(flags, "mock_smells", "low", "loose argument matchers (may not pin the real call)")

    # asset sufficiency (docs/55)
    assets = rs.get("asset_sufficiency") or {}
    if assets.get("business_oracle") == "missing":
        _flag(flags, "asset_sufficiency", "high", "business oracle asset is missing")
    if assets.get("test_level_recommendation") == "manual_oracle_first":
        _flag(flags, "asset_sufficiency", "high", "manual-oracle-first review recommended")
    if assets.get("external_dependency_mock") == "missing":
        _flag(flags, "asset_sufficiency", "medium", "external dependency mock asset is missing")
    if assets.get("test_data") == "missing":
        _flag(flags, "asset_sufficiency", "medium", "test data asset is missing")
    if assets.get("api_schema") == "missing" and assets.get("test_level_recommendation") == "api":
        _flag(flags, "asset_sufficiency", "medium", "API schema asset is missing")
    # Low-noise partial flag: do not emit for the S1 report-local ``existing_tests`` placeholder.
    partial_assets = [
        name for name in (
            "code_context", "business_oracle", "test_data", "api_schema",
            "db_schema", "external_dependency_mock",
        )
        if assets.get(name) == "partial"
    ]
    if partial_assets and not any(f["signal"] == "asset_sufficiency" for f in flags):
        _flag(
            flags,
            "asset_sufficiency",
            "low",
            f"partial asset evidence: {', '.join(partial_assets)}",
        )

    # survived mutants (docs/49)
    sc = (rs.get("mutation_survivors") or {}).get("counts") or {}
    if sc.get("survived_weak_oracle"):
        _flag(flags, "mutation", "medium",
              f"{sc['survived_weak_oracle']} survived mutant(s): assertions miss the change")
    if sc.get("not_covered"):
        _flag(flags, "mutation", "medium",
              f"{sc['not_covered']} uncovered mutant line(s): add a test that exercises them")
    if sc.get("survived_maybe_equivalent"):
        _flag(flags, "mutation", "low",
              f"{sc['survived_maybe_equivalent']} maybe-equivalent survivor(s): review (not auto-bad)")
    if sc.get("survived_unclassified"):
        _flag(flags, "mutation", "low",
              f"{sc['survived_unclassified']} unclassified survivor(s): unrecognized mutator -- review")

    # invariant verification (docs/48) -- only anchoring invariants carry a real estimate
    for item in (rs.get("invariant_review") or {}).get("invariants") or []:
        v = item.get("verified") or {}
        strength = v.get("invariant_strength")
        if not v.get("anchoring"):
            continue
        stmt = (item.get("statement") or "").strip()
        label = f": {stmt}" if stmt else ""
        if strength in ("unaddressed", "addressed_unasserted"):
            _flag(flags, "invariant", "medium", f"declared invariant not pinned{label}")
        elif strength == "asserted_unpinned":
            _flag(flags, "invariant", "low", f"invariant asserted but not mutation-pinned{label}")

    flags.sort(key=lambda f: _SEVERITY_ORDER.get(f["severity"], 9))

    highs = [f for f in flags if f["severity"] == "high"]
    if highs:
        headline = f"needs careful review: {highs[0]['message']}"
    elif flags:
        headline = f"review: {flags[0]['message']}"
    else:
        headline = "no advisory flags (still human review)"

    return {
        "headline": headline,
        "flags": flags,
        "flag_count": len(flags),
        # standing facts -- the digest never accepts and never changes the verdict
        "auto_accept_blocked": True,
        "conclusion": "NEED_HUMAN_REVIEW",
        "advisory": True,
        "note": "advisory roll-up of existing signals; computes nothing new, changes no verdict",
    }
