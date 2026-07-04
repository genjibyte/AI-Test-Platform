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

from app.benchmark.business_tags import normalize_tag
from app.ledger.models import JudgedRecord

_EXAMPLE_CAP = 10


def _filter_kind(records: List[JudgedRecord], run_kind: Optional[str]) -> List[JudgedRecord]:
    """docs/43 S2: restrict to one ``run_kind`` (e.g. headline ``real``). ``None``
    keeps all kinds (back-compat). Historical rows have ``run_kind is None`` and are
    therefore excluded from any specific-kind view (e.g. ``real``)."""
    if run_kind is None:
        return records
    return [r for r in records if r.run_kind == run_kind]


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


def aggregate_badcases(
    records: List[JudgedRecord], *, run_kind: Optional[str] = None
) -> List[BadcaseStat]:
    """Group failing records by signature, most frequent first (ties by signature).
    ``run_kind`` (docs/43 S2): restrict to that kind first; ``real`` = headline."""
    records = _filter_kind(records, run_kind)
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


def author_profile(
    records: List[JudgedRecord], author_id: str, *, run_kind: Optional[str] = None
) -> dict:
    """Usability picture for one author (human / agent / generator) across the ledger.
    ``run_kind`` (docs/43 S2): restrict to that kind first; ``real`` = headline."""
    rs = [
        r
        for r in _filter_kind(records, run_kind)
        if r.provenance.author_id == author_id
    ]
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


def ledger_summary(
    records: List[JudgedRecord], *, top: int = 10, run_kind: Optional[str] = None
) -> dict:
    """One-shot read-only digest of the whole ledger (counts + top badcases + author
    profiles). The single convenience entry over the analytics functions.
    ``run_kind`` (docs/43 S2): restrict to that kind first; ``real`` = headline."""
    records = _filter_kind(records, run_kind)
    authors = sorted({r.provenance.author_id for r in records})
    return {
        "run_kind_filter": run_kind,
        "records": len(records),
        "authors": authors,
        "targets": len(
            {f"{r.target_class}#{r.target_method or '*'}" for r in records}
        ),
        "top_badcases": [s.model_dump() for s in aggregate_badcases(records)[:top]],
        "author_profiles": [author_profile(records, a) for a in authors],
    }


def business_summary(records: List[JudgedRecord], *, run_kind: Optional[str] = None) -> dict:
    """docs/45 S2: descriptive group-by of ledger records by business tag (counts).

    Composes with ``run_kind`` (headline real-only); untagged -> ``unknown``; tags are
    normalized (case-insensitive). Pure description -- no judging, no accept/score."""
    records = _filter_kind(records, run_kind)
    by_domain = Counter(normalize_tag(r.business_domain) or "unknown" for r in records)
    by_pattern = Counter(normalize_tag(r.business_pattern) or "unknown" for r in records)
    return {
        "run_kind_filter": run_kind,
        "records": len(records),
        "by_domain": dict(by_domain.most_common()),
        "by_pattern": dict(by_pattern.most_common()),
    }


def oracle_strength_summary(records: List[JudgedRecord], *, run_kind: Optional[str] = None) -> dict:
    """docs/46 S2: descriptive group-by of ledger records by advisory oracle_strength
    (counts). Composes with ``run_kind`` (headline real-only); un-analyzed -> ``unknown``.
    Pure description -- no judging, no accept/score (the estimate is STRUCTURAL/advisory)."""
    records = _filter_kind(records, run_kind)
    by_strength = Counter((r.oracle_strength or "unknown") for r in records)
    return {
        "run_kind_filter": run_kind,
        "records": len(records),
        "by_oracle_strength": dict(by_strength.most_common()),
    }


def asset_gate_summary(records: List[JudgedRecord], *, run_kind: Optional[str] = None) -> dict:
    """docs/55 S3C: descriptive group-by of compact Asset Gate carry fields.

    Composes with ``run_kind`` and reads already-stored ledger facts only. It does not affect
    badcase signatures, retrieval, or author/target analytics.
    """
    records = _filter_kind(records, run_kind)
    by_level = Counter((r.asset_test_level_recommendation or "unknown") for r in records)
    return {
        "run_kind_filter": run_kind,
        "records": len(records),
        "by_test_level": dict(by_level.most_common()),
        "missing_asset_records": sum(1 for r in records if r.asset_missing_count > 0),
        "partial_asset_records": sum(1 for r in records if r.asset_partial_count > 0),
        "missing_assets_total": sum(r.asset_missing_count for r in records),
        "partial_assets_total": sum(r.asset_partial_count for r in records),
    }
