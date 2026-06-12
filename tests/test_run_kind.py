"""run_kind tests (P1-T3, docs/43). The load-bearing invariant: a fake client can
never yield 'real'. Offline: no model, no pipeline, no .env."""
import pytest

from app.benchmark.models import BenchCaseResult, aggregate
from app.ledger.analytics import ledger_summary, real_records
from app.ledger.ingest import record_from_bench_case
from app.ledger.models import JudgedRecord, Provenance
from app.llm.run_kind import RUN_KINDS, is_real, resolve_run_kind


def test_default_derivation_real_vs_fake():
    assert resolve_run_kind(client_is_fake=False) == "real"
    assert resolve_run_kind(client_is_fake=True) == "fake"


def test_invariant_fake_client_can_never_be_real():
    # THE invariant (owner decision, docs/43 §3): a fake client labeled 'real' is an error.
    with pytest.raises(ValueError):
        resolve_run_kind(client_is_fake=True, override="real")


def test_overrides_are_validated_and_guarded():
    assert resolve_run_kind(client_is_fake=True, override="dryrun") == "dryrun"
    assert resolve_run_kind(client_is_fake=True, override="smoke") == "smoke"
    assert resolve_run_kind(client_is_fake=True, override="FAKE") == "fake"  # case-insensitive
    assert resolve_run_kind(client_is_fake=False, override="real") == "real"
    assert resolve_run_kind(client_is_fake=False, override="smoke") == "smoke"
    with pytest.raises(ValueError):
        resolve_run_kind(client_is_fake=False, override="bogus")
    assert set(RUN_KINDS) == {"real", "fake", "dryrun", "smoke"}


def _case(run_kind):
    return BenchCaseResult(
        name="c", repo_url="u", target_class="C", gen_outcome="PASS",
        passed=True, run_kind=run_kind, conclusion="NEED_HUMAN_REVIEW",
    )


def test_run_kind_carries_into_ledger_record():
    prov = Provenance(author_type="platform_generator", author_id="m")
    assert record_from_bench_case(_case("real"), prov).run_kind == "real"
    assert record_from_bench_case(_case("fake"), prov).run_kind == "fake"
    assert record_from_bench_case(_case(None), prov).run_kind is None


# --- S2: headline = real only (docs/43 §4/§6) ------------------------------------

def test_is_real_only_authoritative_real():
    assert is_real("real") is True
    for k in ("fake", "dryrun", "smoke", None, "REAL", "bogus"):
        assert is_real(k) is False  # strict: unknown/non-real never headline


def _bench(name, run_kind, *, passed):
    return BenchCaseResult(
        name=name, repo_url="u", target_class="C", repo_judged=True,
        generation_status="GEN_DONE",
        gen_outcome="PASS" if passed else "COMPILE_FAILURE",
        compiled=True, executed=True, passed=passed,
        failure_type=None if passed else "COMPILE_FAILURE",
        quality_gate_status="PASS" if passed else "FAIL",
        conclusion="NEED_HUMAN_REVIEW", run_kind=run_kind, runtime_ms=1,
    )


def test_aggregate_headline_real_excludes_nonreal_rows():
    # 1 real pass + 1 fake pass + 1 dryrun fail + 1 unknown(None) fail.
    cases = [
        _bench("r", "real", passed=True),
        _bench("f", "fake", passed=True),
        _bench("d", "dryrun", passed=False),
        _bench("u", None, passed=False),
    ]
    a = aggregate(cases)
    # RAW (all kinds) still sees everything.
    assert a["generation_attempted"] == 4
    assert a["gen_test_pass_rate"] == 0.5          # 2/4 passed across all kinds
    # run_kind provenance surfaced; None -> "unknown", never dropped.
    assert a["run_kind_counts"] == {"real": 1, "fake": 1, "dryrun": 1, "unknown": 1}
    # HEADLINE = real only: the fake PASS cannot inflate it.
    hr = a["headline_real"]
    assert hr["generation_attempted"] == 1
    assert hr["compile_pass_rate"] == 1.0
    assert hr["gen_test_pass_rate"] == 1.0          # the single real row passed
    assert hr["quality_gate_pass_rate"] == 1.0


def _judged(record_id, run_kind, *, passed, failure_type=None):
    return JudgedRecord(
        record_id=record_id, created_at="2026-01-01T00:00:00+00:00",
        repo_url="https://x/r.git", target_class="com.x.C", target_method="m",
        provenance=Provenance(author_type="platform_generator", author_id="gen"),
        failure_type=failure_type, passed=passed, compiled=True, run_kind=run_kind,
    )


def test_ledger_headline_real_excludes_nonreal_rows():
    records = [
        _judged("a", "real", passed=True),
        _judged("b", "fake", passed=False, failure_type="TEST_FAILURE"),
        _judged("c", None, passed=False, failure_type="COMPILE_FAILURE"),
    ]
    assert [r.record_id for r in real_records(records)] == ["a"]
    summ = ledger_summary(records)
    assert summ["records"] == 3                      # raw digest unchanged
    assert summ["run_kind_counts"] == {"real": 1, "fake": 1, "unknown": 1}
    hr = summ["headline_real"]
    assert hr["records"] == 1
    assert hr["pass_rate"] == 1.0
    # the fake TEST_FAILURE and unknown COMPILE_FAILURE are NOT headline badcases.
    assert hr["top_badcases"] == []


def test_smoke_kind_excluded_from_headline_in_both_surfaces():
    # smoke is a "not real" intent kind (docs/43 §6). A smoke PASS -- which would
    # otherwise inflate pass rate -- must stay out of the headline in BOTH the
    # benchmark aggregate and the ledger digest. (is_real covers smoke at the unit
    # level; this closes it at the integration level.)
    a = aggregate([_bench("r", "real", passed=True), _bench("s", "smoke", passed=True)])
    assert a["run_kind_counts"] == {"real": 1, "smoke": 1}
    assert a["gen_test_pass_rate"] == 1.0                     # RAW: both passed
    assert a["headline_real"]["generation_attempted"] == 1    # smoke excluded
    assert a["headline_real"]["gen_test_pass_rate"] == 1.0    # only the real row

    records = [_judged("a", "real", passed=True), _judged("s", "smoke", passed=True)]
    assert [r.record_id for r in real_records(records)] == ["a"]   # smoke filtered out
    hr = ledger_summary(records)["headline_real"]
    assert hr["records"] == 1
    assert hr["pass_rate"] == 1.0
