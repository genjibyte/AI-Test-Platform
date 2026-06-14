"""Badcase retrieval (docs/50 S1) -- ADVISORY: find relevant past judged records as precedent.

Read-only over the precipitation ledger. Returns ONLY real stored records, ranked by EXPLAINABLE
structural similarity (every match carries a reason -- no opaque embeddings). Priors inform human
review; they NEVER auto-accept and change no verdict (``conclusion`` stays ``NEED_HUMAN_REVIEW``).
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.ledger.analytics import badcase_signature
from app.ledger.models import JudgedRecord

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _simple(name: Optional[str]) -> Optional[str]:
    """Last segment of a FQCN (``a.b.Calc`` -> ``Calc``)."""
    return name.rsplit(".", 1)[-1] if name else name


def _tokens(text: Optional[str]) -> set:
    """Lowercase alphanumeric tokens (len > 2) -- a tiny stop-trivial filter, no deps."""
    if not text:
        return set()
    return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2}


def _jaccard(a: set, b: set) -> float:
    """Explainable lexical overlap: |A n B| / |A u B|. 0.0 when either side is empty."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b) if inter else 0.0


def _record_text(rec: JudgedRecord) -> str:
    """All free-text precedent on a record: declared root-cause/fix + invariant statements."""
    parts = [rec.root_cause, rec.fix_note, rec.expected_invariant]
    for inv in (rec.invariants or []):
        if isinstance(inv, dict):
            parts.append(inv.get("statement"))
    return " ".join(p for p in parts if p)


def _score(
    rec: JudgedRecord, *, target_class, target_method, failure_type,
    business_pattern, test_fingerprint, repo_url, query_text=None,
):
    """Explainable similarity of one record to the query -> (score, reasons). Structural signals
    plus an optional no-dependency lexical overlap (``query_text``); every match has a reason."""
    score = 0
    reasons: List[str] = []
    # target match -- most specific wins (mutually exclusive)
    if target_class and rec.target_class == target_class and target_method \
            and rec.target_method == target_method:
        score += 3
        reasons.append("same_target_method")
    elif target_class and rec.target_class == target_class:
        score += 2
        reasons.append("same_target_class")
    elif target_class and _simple(rec.target_class) == _simple(target_class):
        score += 1
        reasons.append("same_simple_class")
    if failure_type and rec.failure_type == failure_type:
        score += 2
        reasons.append("same_failure_type")
    if business_pattern and rec.business_pattern == business_pattern:
        score += 1
        reasons.append("same_business_pattern")
    if test_fingerprint and rec.test_fingerprint == test_fingerprint:
        score += 4
        reasons.append("duplicate_fingerprint")
    if repo_url and rec.repo_url == repo_url:
        score += 1
        reasons.append("same_repo")
    # docs/50 S3: no-dependency, explainable lexical overlap over declared free-text precedent
    # (root-cause/fix/invariant statements). NOT embeddings -- a transparent fallback.
    if query_text:
        jac = _jaccard(_tokens(query_text), _tokens(_record_text(rec)))
        if jac > 0:
            score += round(2 * jac, 4)
            reasons.append("text_overlap")
    return score, reasons


def find_similar(
    records,
    *,
    target_class: str,
    target_method: Optional[str] = None,
    failure_type: Optional[str] = None,
    business_pattern: Optional[str] = None,
    test_fingerprint: Optional[str] = None,
    repo_url: Optional[str] = None,
    query_text: Optional[str] = None,
    top_k: int = 5,
) -> List[dict]:
    """Rank past judged records by explainable similarity to a target (docs/50 S1+S3).

    Structural signals + an optional no-dependency lexical overlap (``query_text`` vs each record's
    declared free-text precedent). ADVISORY + read-only; returns only real records (positive score),
    ranked desc with a recency tiebreak; never raises. Empty input / no match -> ``[]``. No verdict."""
    scored = []
    for rec in records or []:
        s, reasons = _score(
            rec, target_class=target_class, target_method=target_method,
            failure_type=failure_type, business_pattern=business_pattern,
            test_fingerprint=test_fingerprint, repo_url=repo_url, query_text=query_text,
        )
        if s > 0:
            scored.append((s, rec, reasons))
    scored.sort(key=lambda t: (t[0], t[1].created_at or ""), reverse=True)
    return [
        {
            "record_id": rec.record_id,
            "score": s,
            "reasons": reasons,
            "target_class": rec.target_class,
            "target_method": rec.target_method,
            "failure_type": rec.failure_type,
            "conclusion": rec.conclusion,
            "oracle_strength": rec.oracle_strength,
            "mutation_score": rec.mutation_score,
            # docs/50 S2: actionable precedent -- derived signature + declared root-cause/fix.
            "signature": badcase_signature(rec),
            "root_cause": rec.root_cause,
            "fix_note": rec.fix_note,
        }
        for s, rec, reasons in scored[:top_k]
    ]


def find_similar_in_store(store, **query) -> List[dict]:
    """Convenience: ``find_similar`` over the whole ledger (``store.all()``). Read-only."""
    return find_similar(store.all(), **query)
