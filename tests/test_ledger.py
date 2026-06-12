"""Precipitation-layer (ledger) tests (docs/41 P1+P2). Offline: no model, no pipeline."""
import uuid

from app.benchmark.models import BenchCaseResult, BenchReport
from app.ledger.analytics import (
    aggregate_badcases,
    author_profile,
    badcase_signature,
    compare_authors_on_target,
    ledger_summary,
)
from app.ledger.ingest import record_from_bench_case, record_report
from app.ledger.models import JudgedRecord, Provenance, fingerprint_source
from app.ledger.store import LedgerStore


def _case(name, **kw):
    base = dict(
        name=name, repo_url="https://x/r.git", target_class="com.x.C",
        target_method="m", gen_outcome="PASS", compiled=True, executed=True,
        passed=True, failure_type=None, conclusion="NEED_HUMAN_REVIEW",
        quality_gate_status="PASS", review_recommendation="STRONG_REVIEW_CANDIDATE",
    )
    base.update(kw)
    return BenchCaseResult(**base)


def test_fingerprint_normalizes_whitespace_and_handles_none():
    assert fingerprint_source(None) is None
    assert fingerprint_source("   ") is None
    a = fingerprint_source("class T {  void t(){ x(); } }")
    b = fingerprint_source("class T { void t(){ x(); } }")   # whitespace differs only
    assert a == b
    assert a != fingerprint_source("class T { void t(){ y(); } }")  # token differs


def test_record_from_bench_case_projects_facts_and_fingerprint():
    prov = Provenance(author_type="platform_generator", author_id="deepseek-x")
    src = "class T { void t(){ assertEquals(1, f()); } }"
    rec = record_from_bench_case(_case("a", commit_hash="abc123"), prov, test_source=src)
    assert rec.target_class == "com.x.C" and rec.target_method == "m"
    assert rec.ref == "abc123"
    assert rec.passed is True and rec.gen_outcome == "PASS"
    assert rec.review_recommendation == "STRONG_REVIEW_CANDIDATE"
    assert rec.conclusion == "NEED_HUMAN_REVIEW"
    assert rec.provenance.author_type == "platform_generator"
    assert rec.test_fingerprint == fingerprint_source(src)


def test_store_append_query_and_roundtrip(tmp_path):
    store = LedgerStore(tmp_path / "ledger.db")
    p_gen = Provenance(author_type="platform_generator", author_id="gen-v3")
    p_human = Provenance(author_type="human", author_id="alice")
    r1 = record_from_bench_case(_case("a"), p_gen, test_source="class A{}")
    r2 = record_from_bench_case(_case("b", target_method="n"), p_gen)
    r3 = record_from_bench_case(_case("c"), p_human)
    for r in (r1, r2, r3):
        store.append(r)

    assert store.count() == 3
    assert {r.record_id for r in store.all()} == {r1.record_id, r2.record_id, r3.record_id}
    assert {r.record_id for r in store.by_author("alice")} == {r3.record_id}
    assert {r.record_id for r in store.by_target("com.x.C", "m")} == {r1.record_id, r3.record_id}
    assert {r.record_id for r in store.by_target("com.x.C")} == {
        r1.record_id, r2.record_id, r3.record_id}
    assert store.by_fingerprint(fingerprint_source("class A{}"))[0].record_id == r1.record_id

    # roundtrip: the reconstructed record equals the original
    got = next(r for r in store.all() if r.record_id == r1.record_id)
    assert got.model_dump() == r1.model_dump()


def test_append_is_idempotent_on_record_id(tmp_path):
    store = LedgerStore(tmp_path / "ledger.db")
    r = record_from_bench_case(_case("a"), Provenance(author_type="human", author_id="bob"))
    store.append(r)
    store.append(r)  # same record_id -> INSERT OR IGNORE, no duplicate
    assert store.count() == 1


def test_record_report_ingests_all_cases_with_provenance(tmp_path):
    store = LedgerStore(tmp_path / "ledger.db")
    report = BenchReport(
        model="deepseek-x",
        cases=[
            _case("a"),
            _case("b", passed=False, gen_outcome="TEST_FAILURE",
                  failure_type="TEST_FAILURE"),
        ],
    )
    n = record_report(store, report, run_id="run-7")
    assert n == 2 and store.count() == 2

    recs = store.all()
    assert all(r.provenance.author_type == "platform_generator" for r in recs)
    assert all(r.provenance.author_id == "deepseek-x" for r in recs)  # defaults to model
    assert all(r.provenance.run_id == "run-7" for r in recs)
    assert {r.passed for r in recs} == {True, False}
    assert {r.failure_type for r in recs} == {None, "TEST_FAILURE"}


# --- P2 analytics (docs/41 section 5) --------------------------------------------

def _rec(failure_type=None, author="gen", target_class="com.x.C", target_method="m",
         passed=None, compiled=None, recommendation=None, created_at=None, run_kind=None):
    return JudgedRecord(
        record_id=str(uuid.uuid4()),
        created_at=created_at or "2026-01-01T00:00:00+00:00",
        repo_url="https://x/r.git",
        target_class=target_class,
        target_method=target_method,
        provenance=Provenance(author_type="platform_generator", author_id=author),
        failure_type=failure_type,
        passed=passed,
        compiled=compiled,
        review_recommendation=recommendation,
        run_kind=run_kind,
    )


def test_badcase_signature_form_and_none_for_pass():
    assert badcase_signature(_rec(failure_type=None)) is None
    assert badcase_signature(_rec(failure_type="TEST_FAILURE")) == "TEST_FAILURE@com.x.C#m"
    assert badcase_signature(
        _rec(failure_type="COMPILE_FAILURE", target_method=None)
    ) == "COMPILE_FAILURE@com.x.C#*"


def test_aggregate_badcases_groups_counts_and_sorts():
    records = [
        _rec(failure_type="TEST_FAILURE", author="genA", created_at="2026-01-01T00:00:00+00:00"),
        _rec(failure_type="TEST_FAILURE", author="genB", created_at="2026-01-03T00:00:00+00:00"),
        _rec(failure_type="COMPILE_FAILURE", author="genA", created_at="2026-01-02T00:00:00+00:00"),
        _rec(failure_type=None, author="genA"),  # clean PASS -> not a badcase
    ]
    stats = aggregate_badcases(records)
    assert len(stats) == 2                               # PASS ignored
    top = stats[0]
    assert top.signature == "TEST_FAILURE@com.x.C#m"     # count 2 sorts first
    assert top.count == 2
    assert top.authors == ["genA", "genB"]
    assert top.first_seen == "2026-01-01T00:00:00+00:00"
    assert top.last_seen == "2026-01-03T00:00:00+00:00"
    assert len(top.examples) == 2
    assert any(s.failure_type == "COMPILE_FAILURE" and s.count == 1 for s in stats)


def test_author_profile_rates_and_failure_types():
    records = [
        _rec(author="genA", compiled=True, passed=True, recommendation="STRONG_REVIEW_CANDIDATE"),
        _rec(author="genA", compiled=True, passed=False, failure_type="TEST_FAILURE",
             recommendation="NEEDS_REVISION"),
        _rec(author="genB", compiled=False, passed=False, failure_type="COMPILE_FAILURE"),
    ]
    prof = author_profile(records, "genA")
    assert prof["records"] == 2
    assert prof["compile_rate"] == 1.0
    assert prof["pass_rate"] == 0.5
    assert prof["recommendation_distribution"] == {
        "STRONG_REVIEW_CANDIDATE": 1, "NEEDS_REVISION": 1}
    assert prof["top_failure_types"] == {"TEST_FAILURE": 1}


def test_compare_authors_on_target_splits_by_author():
    records = [
        _rec(author="human-alice", target_method="m", compiled=True, passed=True),
        _rec(author="gen-v3", target_method="m", compiled=True, passed=False,
             failure_type="TEST_FAILURE"),
        _rec(author="gen-v3", target_method="other", compiled=True, passed=True),  # diff method
    ]
    cmp = compare_authors_on_target(records, "com.x.C", "m")
    assert cmp["records"] == 2                            # the 'other' method excluded
    assert cmp["authors"] == ["gen-v3", "human-alice"]
    assert cmp["per_author"]["human-alice"]["pass_rate"] == 1.0
    assert cmp["per_author"]["gen-v3"]["pass_rate"] == 0.0
    assert cmp["per_author"]["gen-v3"]["failure_types"] == {"TEST_FAILURE": 1}


def test_ledger_summary_digest():
    records = [
        _rec(author="genA", passed=True),
        _rec(author="genB", failure_type="TEST_FAILURE", passed=False),
    ]
    summ = ledger_summary(records)
    assert summ["records"] == 2
    assert summ["authors"] == ["genA", "genB"]
    assert summ["targets"] == 1
    assert summ["top_badcases"][0]["failure_type"] == "TEST_FAILURE"
    assert len(summ["author_profiles"]) == 2


def test_analytics_run_kind_filter_real_only():
    # docs/43 S2: headline analytics use run_kind == "real"; fake + historical None
    # are excluded. The default (no filter) stays all-kinds for back-compat.
    records = [
        _rec(author="genA", failure_type="TEST_FAILURE", passed=False, run_kind="real"),
        _rec(author="genA", failure_type="TEST_FAILURE", passed=False, run_kind="fake"),
        _rec(author="genB", failure_type="COMPILE_FAILURE", passed=False, run_kind=None),
    ]
    # back-compat: no filter sees all kinds (two distinct signatures)
    assert len(aggregate_badcases(records)) == 2
    # headline real-only: only the one real record survives
    real_bad = aggregate_badcases(records, run_kind="real")
    assert len(real_bad) == 1
    assert real_bad[0].signature == "TEST_FAILURE@com.x.C#m" and real_bad[0].count == 1
    # author_profile honours the filter
    assert author_profile(records, "genA")["records"] == 2
    assert author_profile(records, "genA", run_kind="real")["records"] == 1
    # ledger_summary honours the filter and is self-describing
    assert ledger_summary(records)["run_kind_filter"] is None
    summ = ledger_summary(records, run_kind="real")
    assert summ["run_kind_filter"] == "real" and summ["records"] == 1
