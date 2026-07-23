"""Precipitation-layer (ledger) tests (docs/41 P1+P2). Offline: no model, no pipeline."""
import sqlite3
import uuid

from app.benchmark.models import BenchCaseResult, BenchReport
from app.ledger.analytics import (
    aggregate_badcases,
    asset_gate_summary,
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


def _api_smoke_denominator(**overrides):
    block = {
        "advisory": True,
        "report_only": True,
        "policy_version": "api_smoke_denominator.v1",
        "scope": "separate_api_smoke_denominator",
        "smoke_id": "s7c-junit-api-001",
        "candidate_kind": "junit_api_candidate",
        "run_kind": "fake",
        "eligible_for_api_smoke_denominator": False,
        "benchmark_counting_enabled": False,
        "unit_headline_eligible": False,
        "not_eligible_reasons": ["api_evidence_absent"],
        "requirements": {
            "manifest_present": True,
            "manifest_status_allowed": True,
            "candidate_kind_matches": True,
            "target_matches_generation": True,
            "api_evidence_present": False,
            "api_evidence_candidate_kind_matches": None,
            "runner_tool_matches": None,
            "redaction_contract_satisfied": None,
            "maven_judge_evidence_present": True,
            "conclusion_needs_review": True,
            "trusted_false": True,
        },
    }
    block.update(overrides)
    return block


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


def test_record_from_bench_case_carries_asset_gate_fields_without_changing_signature(tmp_path):
    prov = Provenance(author_type="platform_generator", author_id="deepseek-x")
    src = "class T { void t(){ assertEquals(1, f()); } }"
    rec = record_from_bench_case(
        _case(
            "asset",
            asset_test_level_recommendation="manual_oracle_first",
            asset_missing_count=2,
            asset_partial_count=1,
            failure_type="TEST_FAILURE",
        ),
        prov,
        test_source=src,
    )

    assert rec.asset_test_level_recommendation == "manual_oracle_first"
    assert rec.asset_missing_count == 2
    assert rec.asset_partial_count == 1
    assert badcase_signature(rec) == "TEST_FAILURE@com.x.C#m"

    store = LedgerStore(tmp_path / "ledger.db")
    store.append(rec)
    assert store.by_author("deepseek-x")[0].record_id == rec.record_id
    assert store.by_target("com.x.C", "m")[0].record_id == rec.record_id
    assert store.by_fingerprint(fingerprint_source(src))[0].record_id == rec.record_id
    got = store.all()[0]
    assert got.model_dump() == rec.model_dump()


def test_record_from_bench_case_carries_compact_api_smoke_denominator_fields(tmp_path):
    prov = Provenance(author_type="external_agent", author_id="codex")
    result = _case(
        "api-smoke",
        run_kind="external",
        failure_type="TEST_FAILURE",
        review_summary={
            "api_smoke_denominator": _api_smoke_denominator(),
        },
    )
    rec = record_from_bench_case(result, prov)

    assert rec.run_kind == "external"  # top-level authority; denominator run_kind is not copied
    assert rec.api_smoke_policy_version == "api_smoke_denominator.v1"
    assert rec.api_smoke_scope == "separate_api_smoke_denominator"
    assert rec.api_smoke_smoke_id == "s7c-junit-api-001"
    assert rec.api_smoke_candidate_kind == "junit_api_candidate"
    assert rec.api_smoke_denominator_eligible is False
    assert rec.api_smoke_not_eligible_reasons == ["api_evidence_absent"]
    assert rec.api_smoke_requirement_failures == [
        "api_evidence_present",
        "api_evidence_candidate_kind_matches",
        "runner_tool_matches",
        "redaction_contract_satisfied",
    ]
    assert rec.api_smoke_benchmark_counting_enabled is False
    assert rec.api_smoke_unit_headline_eligible is False
    assert badcase_signature(rec) == "TEST_FAILURE@com.x.C#m"
    assert rec.conclusion == "NEED_HUMAN_REVIEW"

    store = LedgerStore(tmp_path / "ledger.db")
    store.append(rec)
    assert store.all()[0].model_dump() == rec.model_dump()

    with sqlite3.connect(store.db_path) as conn:
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(judged_records)")
        ]
    assert columns == [
        "record_id",
        "created_at",
        "repo_url",
        "target_class",
        "target_method",
        "author_type",
        "author_id",
        "test_fingerprint",
        "gen_outcome",
        "passed",
        "failure_type",
        "conclusion",
        "record_json",
    ]


def test_record_from_bench_case_defaults_api_smoke_fields_for_absent_or_wrong_block():
    prov = Provenance(author_type="platform_generator", author_id="deepseek-x")

    no_block = record_from_bench_case(_case("no-block"), prov)
    assert no_block.api_smoke_policy_version is None
    assert no_block.api_smoke_scope is None
    assert no_block.api_smoke_denominator_eligible is None
    assert no_block.api_smoke_not_eligible_reasons == []
    assert no_block.api_smoke_requirement_failures == []

    wrong_policy = record_from_bench_case(
        _case(
            "wrong-policy",
            review_summary={
                "api_smoke_denominator": _api_smoke_denominator(
                    policy_version="api_smoke_denominator.v2"
                )
            },
        ),
        prov,
    )
    wrong_scope = record_from_bench_case(
        _case(
            "wrong-scope",
            review_summary={
                "api_smoke_denominator": _api_smoke_denominator(
                    scope="unit_headline"
                )
            },
        ),
        prov,
    )

    for rec in (wrong_policy, wrong_scope):
        assert rec.api_smoke_policy_version is None
        assert rec.api_smoke_scope is None
        assert rec.api_smoke_smoke_id is None
        assert rec.api_smoke_candidate_kind is None
        assert rec.api_smoke_denominator_eligible is None
        assert rec.api_smoke_not_eligible_reasons == []
        assert rec.api_smoke_requirement_failures == []
        assert rec.api_smoke_benchmark_counting_enabled is None
        assert rec.api_smoke_unit_headline_eligible is None


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


def test_asset_gate_summary_composes_with_run_kind_and_preserves_signatures():
    records = [
        _rec(
            failure_type="TEST_FAILURE",
            run_kind="real",
            recommendation="NEEDS_REVISION",
        ).model_copy(update={
            "asset_test_level_recommendation": "manual_oracle_first",
            "asset_missing_count": 2,
            "asset_partial_count": 1,
        }),
        _rec(run_kind="real").model_copy(update={
            "asset_test_level_recommendation": "unit",
        }),
        _rec(run_kind="fake").model_copy(update={
            "asset_test_level_recommendation": "api",
            "asset_missing_count": 1,
        }),
        _rec(run_kind="real"),
    ]

    raw = asset_gate_summary(records)
    real = asset_gate_summary(records, run_kind="real")

    assert raw == {
        "run_kind_filter": None,
        "records": 4,
        "by_test_level": {
            "manual_oracle_first": 1,
            "unit": 1,
            "api": 1,
            "unknown": 1,
        },
        "missing_asset_records": 2,
        "partial_asset_records": 1,
        "missing_assets_total": 3,
        "partial_assets_total": 1,
    }
    assert real == {
        "run_kind_filter": "real",
        "records": 3,
        "by_test_level": {
            "manual_oracle_first": 1,
            "unit": 1,
            "unknown": 1,
        },
        "missing_asset_records": 1,
        "partial_asset_records": 1,
        "missing_assets_total": 2,
        "partial_assets_total": 1,
    }
    assert badcase_signature(records[0]) == "TEST_FAILURE@com.x.C#m"
    assert len(aggregate_badcases(records, run_kind="real")) == 1
