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


def invariant_review_view(invariants: List[InvariantDescriptor]) -> dict:
    """docs/48 S1: an ADVISORY surface of the declared invariants for human review.

    ``verified`` is always ``None`` -- S1 carries declarations, it does NOT verify them. A
    non-anchoring (model-declared) invariant is flagged ``anchoring=False`` (cannot self-certify).
    Never a verdict: ``auto_accept_blocked`` stays True; it changes no recommendation/conclusion.
    """
    items = []
    for d in invariants:
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
            "verified": None,                    # S1 does not verify (docs/48 S2/S3)
        })
    return {
        "invariants": items,
        "count": len(items),
        "auto_accept_blocked": True,             # declaring an invariant never accepts a candidate
        "note": "declared intent; S1 carries, does not verify (docs/48)",
    }
