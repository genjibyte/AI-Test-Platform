"""Business-invariant DESCRIPTORS (docs/48 S1) -- declared, carried, NOT yet verified.

A descriptor records *what business property a candidate test is supposed to pin*
(state transition / boundary / exception / side-effect) precisely enough that a later slice
(docs/48 S2/S3) can check whether the test actually addresses + asserts + kills mutants of it.
S1 only *declares and carries* them; it computes no verification and changes no verdict.

Two load-bearing rules (anti-hallucination, docs/48 §2):
- A descriptor is **declared intent, never verified value** -- carrying one never accepts a
  candidate (`auto_accept` stays blocked; `conclusion` stays `NEED_HUMAN_REVIEW`).
- Only a **manifest/human** source can *anchor* real verification later; a **model**-declared
  invariant is UNTRUSTED and may never self-certify (a model's test checked against the same
  model's invariant is circular). `is_anchoring` encodes this.

Non-blocking like the tag vocab (`business_tags.py`): unknown values are allowed and never raise.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.benchmark.business_tags import normalize_tag

# docs/48 §1 -- the invariant kinds we target (extensible; "other"/"unknown" always allowed).
INVARIANT_KINDS = (
    "state_transition", "boundary", "exception", "side_effect", "other", "unknown",
)
# docs/48 §2 -- provenance of the declaration.
INVARIANT_SOURCES = ("manifest", "human", "model", "unknown")
# Only these may anchor a real verification target (everything else cannot self-certify).
ANCHORING_SOURCES = ("manifest", "human")

# docs/48 §4 -- advisory roll-up of how well the candidate TEST pins a declared invariant.
# S2 reaches at most ``asserted_unpinned`` (structural); ``pinned`` needs mutation (S3).
INVARIANT_STRENGTHS = (
    "unaddressed", "addressed_unasserted", "asserted_unpinned", "pinned", "unknown",
)
# oracle_strength (docs/46) buckets -> whether a real (non-weak) assertion exists.
_ASSERTED_TRUE = {"structural_ok", "mixed"}
_ASSERTED_FALSE = {"none", "weak"}


class InvariantDescriptor(BaseModel):
    """One declared business invariant (docs/48 S1). Pure data; carries no verdict."""

    id: Optional[str] = None
    statement: str = ""                       # human-readable property; advisory
    kind: str = "unknown"                      # one of INVARIANT_KINDS
    target_class: Optional[str] = None
    target_method: Optional[str] = None
    target_lines: Optional[str] = None         # e.g. "125" or "130-143"; parsed in S3
    observable: Optional[str] = None           # e.g. "return", "exception:FooException", "state"
    source: str = "unknown"                    # one of INVARIANT_SOURCES


def is_known_kind(value: Optional[str]) -> bool:
    """Advisory predicate -- an unknown kind is allowed, just not a known one."""
    return normalize_tag(value) in INVARIANT_KINDS


def is_known_source(value: Optional[str]) -> bool:
    return normalize_tag(value) in INVARIANT_SOURCES


def is_anchoring(descriptor: InvariantDescriptor) -> bool:
    """docs/48 §2: can this descriptor anchor a real verification target? Only manifest/human
    sources can; a model-declared invariant is untrusted and never self-certifies."""
    return normalize_tag(descriptor.source) in ANCHORING_SOURCES


def parse_invariants(raw: object) -> List[InvariantDescriptor]:
    """Leniently build descriptors from manifest/model data. Never raises (non-blocking):
    ``None`` -> ``[]``; a bare string -> a statement-only descriptor; a dict -> a descriptor
    (unknown keys ignored); malformed entries are skipped."""
    if not raw or not isinstance(raw, (list, tuple)):
        return []
    out: List[InvariantDescriptor] = []
    for item in raw:
        try:
            if isinstance(item, InvariantDescriptor):
                out.append(item)
            elif isinstance(item, str):
                if item.strip():
                    out.append(InvariantDescriptor(statement=item.strip()))
            elif isinstance(item, dict):
                out.append(InvariantDescriptor(**item))
            # anything else: skip silently (non-blocking)
        except Exception:
            continue
    return out


def _derive_asserted(
    descriptor: InvariantDescriptor,
    oracle_strength: Optional[str],
    assertion_names: Optional[List[str]],
) -> Optional[bool]:
    """Does the test carry a right-shape assertion for this invariant? (docs/48 §3, structural)

    Kind-aware when assertion names are available: an ``exception`` invariant wants
    ``assertThrows``. Otherwise reuse the already-computed ``oracle_strength`` (docs/46):
    a real (non-weak) assertion exists iff it is ``structural_ok``/``mixed``. Returns None
    when it cannot be determined."""
    if assertion_names is not None and normalize_tag(descriptor.kind) == "exception":
        return any(a == "assertThrows" for a in assertion_names)
    os = normalize_tag(oracle_strength)
    if os in _ASSERTED_TRUE:
        return True
    if os in _ASSERTED_FALSE:
        return False
    return None


def _inv_result(
    level: str, *, asserted: Optional[bool], addressed: Optional[bool],
    anchoring: bool, reasons: List[str],
) -> dict:
    return {
        "invariant_strength": level,
        "asserted": asserted,
        "addressed": addressed,
        "anchoring": anchoring,
        "reasons": reasons,
        "advisory": True,
        "note": "structural (S2); semantic 'pinned' needs mutation (S3, docs/48)",
    }


def estimate_invariant_strength(
    descriptor: InvariantDescriptor,
    *,
    addressed: Optional[bool] = None,
    oracle_strength: Optional[str] = None,
    assertion_names: Optional[List[str]] = None,
) -> dict:
    """docs/48 S2: advisory STRUCTURAL roll-up of whether the candidate TEST pins a declared
    invariant -- ``addressed`` (coverage reachability) + ``asserted`` (right-shape assertion).
    Pure; never raises; changes no verdict. Reaches at most ``asserted_unpinned`` -- ``pinned``
    requires line-scoped mutation (S3). A non-anchoring (model-declared) invariant is never
    structurally blessed (anti-self-certification, §2) -> ``unknown``."""
    if not is_anchoring(descriptor):
        return _inv_result("unknown", asserted=None, addressed=None,
                           anchoring=False, reasons=["non_anchoring_model_declared"])
    asserted = _derive_asserted(descriptor, oracle_strength, assertion_names)
    reasons: List[str] = []
    if addressed is False:
        level = "unaddressed"
    elif addressed is True and asserted is False:
        level = "addressed_unasserted"
    elif addressed is True and asserted is True:
        level = "asserted_unpinned"              # S2 ceiling; killing mutants is S3
        reasons.append("pinned_needs_mutation")
    else:
        # cannot confirm reachability (coverage often skipped) and/or assertion strength
        level = "unknown"
        if addressed is None:
            reasons.append("coverage_unavailable")
        if asserted is None:
            reasons.append("assertion_strength_unknown")
    return _inv_result(level, asserted=asserted, addressed=addressed,
                       anchoring=True, reasons=reasons)


def invariant_review_view(
    invariants: List[InvariantDescriptor],
    *,
    verify: bool = False,
    oracle_strength: Optional[str] = None,
    addressed: Optional[bool] = None,
    assertion_names: Optional[List[str]] = None,
) -> dict:
    """ADVISORY surface of the declared invariants for human review (docs/48 S1 + S2).

    ``verify=False`` (S1): ``verified`` stays ``None`` -- declarations are only carried. With
    ``verify=True`` (S2): each ANCHORING invariant gets a structural ``estimate_invariant_strength``
    in ``verified`` (non-anchoring ones still surface ``unknown`` -- they never self-certify).
    Never a verdict: ``auto_accept_blocked`` stays True; it changes no recommendation/conclusion.
    """
    items = []
    for d in invariants:
        verified = None
        if verify:
            verified = estimate_invariant_strength(
                d, addressed=addressed, oracle_strength=oracle_strength,
                assertion_names=assertion_names,
            )
        items.append({
            "id": d.id,
            "statement": d.statement,
            "kind": normalize_tag(d.kind) or "unknown",
            "source": normalize_tag(d.source) or "unknown",
            "anchoring": is_anchoring(d),       # only manifest/human can anchor verification
            "target_class": d.target_class,
            "target_method": d.target_method,
            "target_lines": d.target_lines,
            "observable": d.observable,
            "verified": verified,                # None (S1) or structural estimate (S2)
        })
    return {
        "invariants": items,
        "count": len(items),
        "auto_accept_blocked": True,             # declaring an invariant never accepts a candidate
        "note": "declared intent; verification is structural + advisory (docs/48 S1/S2)",
    }
