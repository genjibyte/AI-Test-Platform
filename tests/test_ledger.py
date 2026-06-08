"""Precipitation-layer (ledger) tests (docs/41 P1). Offline: no model, no pipeline."""
from app.benchmark.models import BenchCaseResult, BenchReport
from app.ledger.ingest import record_from_bench_case, record_report
from app.ledger.models import Provenance, fingerprint_source
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
