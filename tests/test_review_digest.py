"""Review digest tests (docs/52). Offline; pure; ADVISORY -- the digest rolls up existing signals
into a prioritized checklist and changes NO verdict (auto_accept stays blocked).
"""
from app.review.review_digest import build_review_digest

_SEV = {"high": 0, "medium": 1, "low": 2, "info": 3}


def test_oracle_none_is_high_and_drives_headline():
    d = build_review_digest({"oracle_strength_estimate": {"oracle_strength": "none"}})
    assert d["flags"][0]["severity"] == "high" and d["flags"][0]["signal"] == "oracle_strength"
    assert d["headline"].startswith("needs careful review")


def test_mock_of_target_is_high():
    d = build_review_digest({"mock_smells": {"counts": {"mock_of_target": 1}}})
    assert any(f["severity"] == "high" and f["signal"] == "mock_smells" for f in d["flags"])


def test_mutation_and_invariant_flags_with_non_anchoring_skipped():
    rs = {
        "mutation_survivors": {"counts": {"survived_weak_oracle": 2, "survived_maybe_equivalent": 1}},
        "invariant_review": {"invariants": [
            {"statement": "x", "verified": {"anchoring": True, "invariant_strength": "addressed_unasserted"}},
            {"statement": "m", "verified": {"anchoring": False, "invariant_strength": "unknown"}},
        ]},
    }
    d = build_review_digest(rs)
    sigs = {(f["signal"], f["severity"]) for f in d["flags"]}
    assert ("mutation", "medium") in sigs           # survived_weak_oracle
    assert ("mutation", "low") in sigs              # maybe_equivalent
    assert ("invariant", "medium") in sigs          # anchoring addressed_unasserted
    assert sum(1 for f in d["flags"] if f["signal"] == "invariant") == 1   # non-anchoring skipped


def test_mutation_unclassified_survivor_is_low_flag():
    # a survivor the classifier couldn't bucket (unrecognized mutator) must still reach the
    # digest -- survivors.py marks it "human review"; report_md surfaces it; the digest must too.
    d = build_review_digest({"mutation_survivors": {"counts": {"survived_unclassified": 2}}})
    assert any(f["signal"] == "mutation" and f["severity"] == "low" for f in d["flags"])
    assert "unclassified" in d["flags"][0]["message"]


def test_quality_blockers_are_high():
    d = build_review_digest({"quality": {"blockers": ["no_assertions"]}})
    assert d["flags"][0]["signal"] == "quality_gate" and d["flags"][0]["severity"] == "high"


def test_no_signals_is_clean_but_still_human_review():
    d = build_review_digest({})
    assert d["flag_count"] == 0 and "no advisory flags" in d["headline"]
    assert d["auto_accept_blocked"] is True and d["conclusion"] == "NEED_HUMAN_REVIEW"


def test_flags_sorted_high_before_low():
    rs = {"oracle_strength_estimate": {"oracle_strength": "none"},       # high
          "mock_smells": {"counts": {"stub_returns_null": 1}}}          # low
    sev = [f["severity"] for f in build_review_digest(rs)["flags"]]
    assert sev == sorted(sev, key=lambda s: _SEV[s])


def test_digest_is_always_advisory_and_never_accepts():
    d = build_review_digest({"oracle_strength_estimate": {"oracle_strength": "weak"}})
    assert d["auto_accept_blocked"] is True and d["conclusion"] == "NEED_HUMAN_REVIEW"
    assert d["advisory"] is True


# --- wiring -----------------------------------------------------------------------

def test_generation_report_attaches_digest_without_changing_verdict():
    from app.report.generation_report import CONCLUSION, assemble_generation_report

    src = "package com.example; class T { void t(){ Calc c = mock(Calc.class); } }"
    bundle = {
        "target": {"target_class": "com.example.Calc", "target_method": "max"},
        "result": {"test_source": src, "model": "fake-1", "trusted": False},
        "write": {"created": True, "production_code_touched": False, "content": src},
        "execution": {"gen_outcome": "PASS", "build_outcome": "SUCCESS",
                      "gen_total": 1, "gen_passed": 1, "gen_failed": 0,
                      "gen_errors": 0, "gen_skipped": 0},
        "error": None,
    }
    dg = assemble_generation_report(bundle)["review_summary"]["digest"]
    assert "flags" in dg and dg["conclusion"] == "NEED_HUMAN_REVIEW"
    # the mock_of_target smell makes it into the digest
    assert any(f["signal"] == "mock_smells" for f in dg["flags"])
    assert assemble_generation_report(bundle)["conclusion"] == CONCLUSION


def test_attach_digest_includes_benchmark_layer_signals():
    from app.benchmark import runner as R
    from app.benchmark.models import BenchCaseResult

    result = BenchCaseResult(
        name="c", repo_url="u", target_class="C", conclusion="NEED_HUMAN_REVIEW",
        review_summary={"mutation_survivors": {"counts": {"survived_weak_oracle": 1}}},
    )
    R._attach_digest(result)
    dg = result.review_summary["digest"]
    assert any(f["signal"] == "mutation" for f in dg["flags"])
    assert result.conclusion == "NEED_HUMAN_REVIEW"      # verdict never changes
