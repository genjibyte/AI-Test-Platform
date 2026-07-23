"""Precipitation / accumulation layer (docs/41).

A source-agnostic, cross-run, queryable ledger of JUDGING results. Records come
from any producer -- the platform generator (via the benchmark), an external agent,
or a human -- and carry the judging facts already computed by the pipeline. This
package only persists and queries facts; it never judges, repairs, or accepts.

P1 scope (this slice): the ``JudgedRecord`` model, a SQLite ``LedgerStore`` (append +
basic by-target/by-author queries), and the ``BenchCaseResult -> JudgedRecord``
ingest adapter. Badcase signatures (P2) and the author-agnostic submit entry (P3)
are designed in docs/41 but NOT built here.
"""
from app.ledger.models import AUTHOR_TYPES, JudgedRecord, Provenance, fingerprint_source
from app.ledger.store import LedgerStore
from app.ledger.ingest import record_from_bench_case, record_report
from app.ledger.analytics import (
    BadcaseStat,
    aggregate_badcases,
    author_profile,
    badcase_signature,
    business_summary,
    compare_authors_on_target,
    ledger_summary,
    oracle_strength_summary,
)
from app.ledger.api_smoke_projection import api_smoke_ledger_projection
from app.ledger.api_smoke_report import render_api_smoke_ledger_markdown
from app.ledger.retrieval import find_similar, find_similar_in_store

__all__ = [
    "AUTHOR_TYPES",
    "JudgedRecord",
    "Provenance",
    "fingerprint_source",
    "LedgerStore",
    "record_from_bench_case",
    "record_report",
    # analytics (P2)
    "BadcaseStat",
    "badcase_signature",
    "aggregate_badcases",
    "author_profile",
    "business_summary",
    "compare_authors_on_target",
    "ledger_summary",
    "oracle_strength_summary",
    # S10B named projection; not wired into existing analytics summaries
    "api_smoke_ledger_projection",
    # S10C presentation helper; still not wired into existing analytics summaries
    "render_api_smoke_ledger_markdown",
    # retrieval (#6 S1, docs/50)
    "find_similar",
    "find_similar_in_store",
]
