"""Manifest v2 = v1 pins ENRICHED with the value-judgment dimension (docs/23/45/48).

Offline. v2 must (1) load, (2) keep v1's exact code-under-test (same target->commit
pins, so v1's reproducibility/baseline is untouched), and (3) carry business-invariant
tags + ANCHORING invariant descriptors on every case (manifest-declared, advisory).
These are declared intent, never verified value -- they change no verdict.
"""
import json
from pathlib import Path

from app.benchmark.business_tags import is_known_domain, is_known_pattern, is_known_risk
from app.benchmark.invariants import is_anchoring, is_known_kind
from app.benchmark.models import load_spec

_BENCH = Path(__file__).resolve().parent.parent / "benchmarks"
V1 = _BENCH / "manifest.v1.json"
V2 = _BENCH / "manifest.v2.json"


def _cases(path):
    return load_spec(json.loads(path.read_text(encoding="utf-8")))


def test_v2_loads_same_count_as_v1():
    assert len(_cases(V2)) == len(_cases(V1)) == 10


def test_v2_keeps_v1_exact_pins():
    """Same target -> same repo+commit as v1: identical code-under-test (v1 stays the
    frozen reproducibility pin; v2 only adds advisory metadata)."""
    v1 = {c.target_class: (c.repo_url, c.commit) for c in _cases(V1)}
    v2 = {c.target_class: (c.repo_url, c.commit) for c in _cases(V2)}
    assert v2 == v1


def test_v2_every_case_has_known_business_tags():
    for c in _cases(V2):
        assert c.business_domain and is_known_domain(c.business_domain), c.label()
        assert c.business_pattern and is_known_pattern(c.business_pattern), c.label()
        assert c.risk_level and is_known_risk(c.risk_level), c.label()
        assert c.expected_invariant, c.label()


def test_v2_every_case_has_anchoring_invariants():
    for c in _cases(V2):
        assert c.invariants, f"{c.label()} declares no invariants"
        for inv in c.invariants:
            # manifest-declared -> anchoring (may drive real verification, docs/48 S2)
            assert inv.source == "manifest" and is_anchoring(inv), c.label()
            assert is_known_kind(inv.kind), f"{c.label()}: unknown kind {inv.kind}"
            assert inv.statement.strip(), c.label()
            # method-scoped so docs/48 _scope + docs/49 survivors can use it w/o line spec
            assert inv.target_method, f"{c.label()}: invariant not method-scoped"


def test_v2_invariant_view_verifies_and_never_accepts():
    """An anchoring invariant flows through the advisory verifier without accepting."""
    from app.benchmark.invariants import invariant_review_view

    case = next(c for c in _cases(V2) if c.target_class.endswith("Validate"))
    view = invariant_review_view(list(case.invariants), verify=True,
                                 oracle_strength="structural_ok")
    assert view["auto_accept_blocked"] is True
    assert view["count"] == len(case.invariants)
    assert all(item["anchoring"] for item in view["invariants"])
