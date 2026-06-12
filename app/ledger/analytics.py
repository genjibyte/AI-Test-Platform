"""Ledger analytics (docs/41 P2): badcase signatures + read-only views.

Deterministic aggregation over ``JudgedRecord``s already in the ledger. No model, no
judging, no rule generation -- it only counts and groups facts the pipeline produced.
Badcase signatures are COARSE in P2 (``failure_type @ target``); finer signatures
(expected/actual class, compile-error class) are designed in docs/41 section 4 for
later and need no schema change (they would refine ``badcase_signature`` only).

All functions take a ``list[JudgedRecord]`` (e.g. ``store.all()`` /
``store.by_target(...)``) so they are pure and testable without a DB.
"""
from __future__ import annotations

from collections import Counter
from typing import Callable, List, Optional

from pydantic import BaseModel, Field

from app.ledger.models import JudgedRecord
from app.llm.run_kind import is_real

_EXAMPLE_CAP = 10


def real_records(records: List[JudgedRecord]) -> List[JudgedRecord]:
    """Authoritative ``real``-only subset for headline metrics (docs/43 §4). Excludes
    fake/dryrun/smoke and None (historical / no field). The other analytics functions
    stay pure over whatever list they're given; callers filter via this helper, and
    ``ledger_summary`` exposes a real-only headline block alongside the raw digest."""
    return [r for r in records if is_real(r.run_kind)]


def badcase_signature(record: JudgedRecord) -> Optional[str]:
    """A coarse, deterministic failure signature, or ``None`` for a non-failing
    record. Form: ``<failure_type>@<target_class>#<target_method|*>``. The
    ``failure_type`` prefix keeps infra failures (REPO_*/LLM_CONFIG_*) distinguishable
    from test failures (COMPILE_FAILURE/TEST_FAILURE/...)."""
    if not record.failure_type:
        return None
    return f"{record.failure_type}@{record.target_class}#{record.target_method or '*'}"


class BadcaseStat(BaseModel):
    """Aggregated recurrence of one failure signature across the ledger."""

    signature: str
    failure_type: str
    count: int
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    authors: List[str] = Field(default_factory=list)   # author_ids that hit it
    targets: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)   # record_ids (capped)


def aggregate_badcases(records: List[JudgedRecord]) -> List[BadcaseStat]:
    """Group failing records by signature, most frequent first (ties by signature)."""
    groups: dict[str, List[JudgedRecord]] = {}
    for r in records:
        sig = badcase_signature(r)
        if sig is not None:
            groups.setdefault(sig, []).append(r)

    stats: List[BadcaseStat] = []
    for sig, rs in groups.items():
        times = sorted(r.created_at for r in rs)
        stats.append(
            BadcaseStat(
                signature=sig,
                failure_type=rs[0].failure_type,
                count=len(rs),
                first_seen=times[0],
                last_seen=times[-1],
                authors=sorted({r.provenance.author_id for r in rs}),
                targets=sorted(
                    {f"{r.target_class}#{r.target_method or '*'}" for r in rs}
                ),
                examples=[r.record_id for r in rs[:_EXAMPLE_CAP]],
            )
        )
    stats.sort(key=lambda s: (-s.count, s.signature))
    return stats


def _rate(records: List[JudgedRecord], pred: Callable[[JudgedRecord], bool]) -> Optional[float]:
    if not records:
        return None
    return round(sum(1 for r in records if pred(r)) / len(records), 4)


def author_profile(records: List[JudgedRecord], author_id: str) -> dict:
    """Usability picture for one author (human / agent / generator) across the ledger."""
    rs = [r for r in records if r.provenance.author_id == author_id]
    return {
        "author_id": author_id,
        "records": len(rs),
        "compile_rate": _rate(rs, lambda r: r.compiled is True),
        "pass_rate": _rate(rs, lambda r: r.passed is True),
        "recommendation_distribution": dict(
            Counter(
                r.review_recommendation for r in rs if r.review_recommendation
            ).most_common()
        ),
        "top_failure_types": dict(
            Counter(r.failure_type for r in rs if r.failure_type).most_common()
        ),
        "top_badcases": [s.model_dump() for s in aggregate_badcases(rs)[:5]],
    }


def compare_authors_on_target(
    records: List[JudgedRecord],
    target_class: str,
    target_method: Optional[str] = None,
) -> dict:
    """Cross-author comparison on ONE target (docs/41 section 5): per author, the
    judging outcomes on the same target -- "who judges better, not who generates
    more". Records may come from any producer (human / agent / generator)."""
    rs = [
        r
        for r in records
        if r.target_class == target_class
        and (target_method is None or r.target_method == target_method)
    ]
    authors = sorted({r.provenance.author_id for r in rs})
    per_author = {}
    for a in authors:
        ars = [r for r in rs if r.provenance.author_id == a]
        per_author[a] = {
            "records": len(ars),
            "compile_rate": _rate(ars, lambda r: r.compiled is True),
            "pass_rate": _rate(ars, lambda r: r.passed is True),
            "failure_types": dict(
                Counter(r.failure_type for r in ars if r.failure_type).most_common()
            ),
        }
    return {
        "target": f"{target_class}#{target_method or '*'}",
        "records": len(rs),
        "authors": authors,
        "per_author": per_author,
    }


def ledger_summary(records: List[JudgedRecord], *, top: int = 10) -> dict:
    """One-shot read-only digest of the whole ledger (counts + top badcases + author
    profiles). The single convenience entry over the analytics functions.

    The top-level digest is RAW (all run_kinds). ``run_kind_counts`` surfaces the
    provenance split (None -> "unknown", never dropped) and ``headline_real`` is the
    authoritative real-only view (docs/43 §4): real compile/pass rates and badcases so
    fake/dryrun/smoke can never inflate the ledger headline."""
    authors = sorted({r.provenance.author_id for r in records})
    real = real_records(records)
    return {
        "records": len(records),
        "authors": authors,
        "targets": len(
            {f"{r.target_class}#{r.target_method or '*'}" for r in records}
        ),
        "top_badcases": [s.model_dump() for s in aggregate_badcases(records)[:top]],
        "author_profiles": [author_profile(records, a) for a in authors],
        "run_kind_counts": dict(
            Counter((r.run_kind or "unknown") for r in records).most_common()
        ),
        "headline_real": {
            "records": len(real),
            "compile_rate": _rate(real, lambda r: r.compiled is True),
            "pass_rate": _rate(real, lambda r: r.passed is True),
            "top_badcases": [s.model_dump() for s in aggregate_badcases(real)[:top]],
        },
    }
