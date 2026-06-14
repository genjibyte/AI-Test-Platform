"""Survived-mutant classification (docs/49 S1) -- ADVISORY explanation of why mutants survived.

Equivalence is **undecidable**, so this NEVER asserts a mutant is equivalent and NEVER condemns a
test because a mutant survived. It buckets the decidable facts (not-covered vs covered-but-survived)
and attaches a mutator-based explanation + an ``equivalence_likelihood`` hint so a human can review
(docs/46 §16 showed both kinds on real code). It changes no verdict: ``conclusion`` stays
``NEED_HUMAN_REVIEW``; nothing is auto-accepted.
"""
from __future__ import annotations

from typing import Optional

# A mutant is "detected" (killed) for these statuses -- NOT a survivor.
_DETECTED = {"KILLED", "TIMED_OUT"}

# SURVIVED on these is rarely an equivalent mutant -> likely a real weak oracle (actionable).
_WEAK_ORACLE_MUTATORS = {
    "MathMutator", "NegateConditionalsMutator", "PrimitiveReturnsMutator",
    "EmptyObjectReturnValsMutator", "BooleanTrueReturnValsMutator",
    "BooleanFalseReturnValsMutator", "NullReturnValsMutator", "InlineConstantMutator",
}
# SURVIVED on these is OFTEN equivalent in practice -> flag for review (never asserted equivalent).
_MAYBE_EQUIVALENT_MUTATORS = {
    "ConditionalsBoundaryMutator", "VoidMethodCallMutator", "IncrementsMutator",
}

_EXPLANATIONS = {
    "MathMutator": "replaced an arithmetic operator; the test runs the code but does not check the result",
    "ConditionalsBoundaryMutator": "changed a conditional boundary (e.g. > to >=); may be unreachable/equivalent -- review",
    "NegateConditionalsMutator": "negated a conditional; the test does not distinguish the branches",
    "PrimitiveReturnsMutator": "replaced a primitive return with a default; the test does not assert the return value",
    "EmptyObjectReturnValsMutator": "replaced an object return with empty/null; the test does not assert the return value",
    "VoidMethodCallMutator": "removed a void method call; may be side-effect-free/equivalent -- review",
    "IncrementsMutator": "changed an increment; may be equivalent if the value is unused -- review",
}


def _classify_one(row: dict) -> dict:
    status = (row.get("status") or "").upper()
    mutator = row.get("mutator") or ""
    if status == "NO_COVERAGE":
        category, likelihood = "not_covered", "none"
        explanation = "the test never executes this line (coverage gap) -- add a test that exercises it"
    elif mutator in _MAYBE_EQUIVALENT_MUTATORS:
        category, likelihood = "survived_maybe_equivalent", "medium"
        explanation = _EXPLANATIONS.get(mutator, "survived; this mutator is often equivalent -- review")
    elif mutator in _WEAK_ORACLE_MUTATORS:
        category, likelihood = "survived_weak_oracle", "low"
        explanation = _EXPLANATIONS.get(mutator, "survived; the test runs the code but does not catch the change")
    else:
        category, likelihood = "survived_unclassified", "unknown"
        explanation = "survived; unrecognized mutator -- human review"
    return {
        "line": row.get("line"),
        "method": row.get("method"),
        "mutator": mutator,
        "status": status,
        "category": category,
        "explanation": explanation,
        "equivalence_likelihood": likelihood,   # how likely this survivor is an EQUIVALENT mutant
    }


def classify_survivors(mutations: Optional[list]) -> dict:
    """Bucket the non-killed mutants with advisory explanations (docs/49 S1). Pure; never raises;
    changes no verdict. KILLED/TIMED_OUT are not survivors. Empty/None -> zero survivors."""
    rows = mutations or []
    survivors = [
        _classify_one(r) for r in rows
        if (r.get("status") or "").upper() not in _DETECTED
    ]
    counts = {
        "not_covered": 0, "survived_weak_oracle": 0,
        "survived_maybe_equivalent": 0, "survived_unclassified": 0,
    }
    for s in survivors:
        counts[s["category"]] = counts.get(s["category"], 0) + 1
    return {
        "survivors": survivors,
        "counts": counts,
        "total_survivors": len(survivors),
        "advisory": True,
        "note": "explanation only; survival is not proof a test is weak (equivalence undecidable)",
    }
