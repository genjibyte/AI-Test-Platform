"""submit_candidate S2 tests (docs/53 S2): provenance is first-class, and the
charter invariant -- *an external candidate never enters the 'real' headline* --
is enforced by the EXISTING generic run_kind filter (no new analytics code; this
is the proof-by-test the design calls for). Offline; no Maven; no LLM.
"""
from __future__ import annotations

from app.benchmark.models import BenchCaseResult, aggregate
from app.ledger.analytics import aggregate_badcases
from app.ledger.ingest import record_from_bench_case
from app.ledger.models import Provenance
from app.report.generation_report import assemble_generation_report


def _case(run_kind, **kw):
    base = dict(
        name="c", repo_url="u", target_class="C", gen_outcome="PASS",
        passed=True, run_kind=run_kind, conclusion="NEED_HUMAN_REVIEW",
    )
    base.update(kw)
    return BenchCaseResult(**base)


# ---- charter invariant: external never enters the real headline ---------------

def test_external_excluded_from_real_headline_aggregate():
    cases = [_case("real"), _case("real"), _case("external")]
    real = aggregate(cases, run_kind="real")
    assert real["run_kind_filter"] == "real"
    assert real["total_cases"] == 2          # the external row is NOT counted


def test_external_only_aggregate_view():
    cases = [_case("real"), _case("external"), _case("external")]
    ext = aggregate(cases, run_kind="external")
    assert ext["run_kind_filter"] == "external"
    assert ext["total_cases"] == 2           # only the external rows


def test_all_kinds_view_includes_external():
    cases = [_case("real"), _case("external")]
    assert aggregate(cases)["total_cases"] == 2   # run_kind=None keeps all


def test_external_cannot_masquerade_as_real_in_headline():
    """The load-bearing parallel to 'fake can never be real': a pile of external
    rows must not inflate the real headline even if they all 'passed'."""
    cases = [_case("external", passed=True) for _ in range(5)]
    real = aggregate(cases, run_kind="real")
    assert real["total_cases"] == 0
    assert real["gen_test_pass_rate"] is None     # nothing real -> no rate


# ---- ledger analytics compose the same way ------------------------------------

def _rec(run_kind):
    prov = Provenance(author_type="platform_generator", author_id="m")
    case = _case(run_kind, gen_outcome="TEST_FAILURE", passed=False,
                 failure_type="TEST_FAILURE")
    return record_from_bench_case(case, prov)


def test_ledger_real_headline_excludes_external():
    recs = [_rec("real"), _rec("external")]
    assert sum(s.count for s in aggregate_badcases(recs, run_kind="real")) == 1
    assert sum(s.count for s in aggregate_badcases(recs, run_kind="external")) == 1
    assert sum(s.count for s in aggregate_badcases(recs)) == 2


# ---- provenance is first-class in the per-candidate report --------------------

def _bundle(run_kind, producer_id):
    res = {
        "target_class": "com.example.Calc", "target_method": "max",
        "test_class_name": "T", "model": producer_id, "trusted": False,
        "producer_id": producer_id, "test_source": "class T {}",
    }
    return {
        "target": {"target_class": "com.example.Calc", "target_method": "max"},
        "result": res,
        "write": {"created": True, "production_code_touched": False, "content": "class T {}"},
        "execution": {"gen_outcome": "PASS", "build_outcome": "SUCCESS",
                      "gen_total": 1, "gen_passed": 1, "gen_failed": 0,
                      "gen_errors": 0, "gen_skipped": 0},
        "error": None, "run_kind": run_kind, "producer_id": producer_id,
    }


def test_report_surfaces_producer_and_run_kind_for_submit():
    r = assemble_generation_report(_bundle("external", "claude-4-7"))
    assert r["producer_id"] == "claude-4-7"
    assert r["run_kind"] == "external"
    # provenance is NEVER a warrant
    assert r["trusted"] is False
    assert r["conclusion"] == "NEED_HUMAN_REVIEW"


def test_report_generator_path_producer_id_is_none():
    """Back-compat: a generator bundle has no producer_id; run_kind is real."""
    b = _bundle("real", None)
    r = assemble_generation_report(b)
    assert r["producer_id"] is None
    assert r["run_kind"] == "real"


def test_report_producer_id_falls_back_to_bundle_when_result_missing_it():
    """If an older bundle lacks result.producer_id but has the top-level one."""
    b = _bundle("external", "codex-cli")
    b["result"].pop("producer_id")
    r = assemble_generation_report(b)
    assert r["producer_id"] == "codex-cli"
