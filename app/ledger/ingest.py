"""Ingest adapter: project a judged benchmark case into a ledger record (docs/41).

The benchmark is one producer of judged records. ``record_from_bench_case`` maps the
existing ``BenchCaseResult`` facts (+ provenance, + optional source fingerprint) onto
a ``JudgedRecord``; ``record_report`` ingests a whole ``BenchReport``. No judging
logic runs here -- it only copies facts the pipeline already computed.
"""
from __future__ import annotations

import uuid
from typing import Optional

from app.benchmark.models import BenchCaseResult, BenchReport
from app.ledger.models import JudgedRecord, Provenance, fingerprint_source
from app.ledger.store import LedgerStore


def record_from_bench_case(
    result: BenchCaseResult,
    provenance: Provenance,
    test_source: Optional[str] = None,
) -> JudgedRecord:
    """Project one BenchCaseResult onto a JudgedRecord (judging facts only)."""
    return JudgedRecord(
        record_id=str(uuid.uuid4()),
        repo_url=result.repo_url,
        ref=result.commit_hash,
        target_class=result.target_class,
        target_method=result.target_method,
        provenance=provenance,
        test_fingerprint=fingerprint_source(test_source),
        run_kind=result.run_kind,
        business_domain=result.business_domain,
        business_pattern=result.business_pattern,
        expected_invariant=result.expected_invariant,
        risk_level=result.risk_level,
        invariants=[i.model_dump() for i in result.invariants],  # docs/48 S1 (advisory)
        oracle_strength=result.oracle_strength,
        mutation_score=result.mutation_score,
        asset_test_level_recommendation=result.asset_test_level_recommendation,
        asset_missing_count=result.asset_missing_count,
        asset_partial_count=result.asset_partial_count,
        gen_outcome=result.gen_outcome,
        compiled=result.compiled,
        executed=result.executed,
        passed=result.passed,
        failure_type=result.failure_type,
        coverage_status=result.coverage_status,
        target_improved=result.target_improved,
        coverage_dropped=result.coverage_dropped,
        quality_gate_status=result.quality_gate_status,
        quality_blockers=result.quality_blockers,
        quality_warnings=result.quality_warnings,
        review_recommendation=result.review_recommendation,
        conclusion=result.conclusion,
    )


def record_report(
    store: LedgerStore,
    report: BenchReport,
    *,
    author_type: str = "platform_generator",
    author_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> int:
    """Append every case of a benchmark report to the ledger. Returns the count.

    The platform generator is the author; ``author_id`` defaults to the report's
    model. (P1 omits per-case test_source, so fingerprints are None here; the adapter
    computes them when a source is supplied -- e.g. a future external-agent submit.)"""
    author_id = author_id or report.model or "unknown"
    n = 0
    for case in report.cases:
        prov = Provenance(
            author_type=author_type,
            author_id=author_id,
            model=report.model,
            run_id=run_id,
        )
        store.append(record_from_bench_case(case, prov))
        n += 1
    return n
