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

__all__ = [
    "AUTHOR_TYPES",
    "JudgedRecord",
    "Provenance",
    "fingerprint_source",
    "LedgerStore",
    "record_from_bench_case",
    "record_report",
]
