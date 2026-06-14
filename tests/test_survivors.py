"""Survived-mutant classification tests (docs/49 S1). Offline; pure; advisory -- classification
explains survivors and changes NO verdict (equivalence is undecidable; nothing is asserted equiv).
"""
from app.mutation import classify_survivors


def _row(status, mutator="MathMutator", line=10, method="m"):
    return {"line": line, "method": method, "status": status, "mutator": mutator,
            "detected": status in {"KILLED", "TIMED_OUT"}}


def test_killed_and_timed_out_are_not_survivors():
    r = classify_survivors([_row("KILLED"), _row("TIMED_OUT")])
    assert r["total_survivors"] == 0 and r["survivors"] == []


def test_no_coverage_is_a_coverage_gap_not_equivalence():
    s = classify_survivors([_row("NO_COVERAGE")])["survivors"][0]
    assert s["category"] == "not_covered" and s["equivalence_likelihood"] == "none"
    assert "coverage gap" in s["explanation"]


def test_survived_math_is_weak_oracle_low_equivalence():
    s = classify_survivors([_row("SURVIVED", "MathMutator")])["survivors"][0]
    assert s["category"] == "survived_weak_oracle" and s["equivalence_likelihood"] == "low"


def test_survived_conditional_boundary_is_maybe_equivalent():
    s = classify_survivors([_row("SURVIVED", "ConditionalsBoundaryMutator")])["survivors"][0]
    assert s["category"] == "survived_maybe_equivalent" and s["equivalence_likelihood"] == "medium"
    assert "review" in s["explanation"].lower()


def test_survived_unknown_mutator_is_unclassified():
    s = classify_survivors([_row("SURVIVED", "SomeNewMutator")])["survivors"][0]
    assert s["category"] == "survived_unclassified" and s["equivalence_likelihood"] == "unknown"


def test_counts_rollup_and_total():
    r = classify_survivors([
        _row("KILLED"),                                  # not a survivor
        _row("NO_COVERAGE"),                             # not_covered
        _row("SURVIVED", "MathMutator"),                 # weak_oracle
        _row("SURVIVED", "ConditionalsBoundaryMutator"), # maybe_equivalent
        _row("SURVIVED", "Mystery"),                     # unclassified
    ])
    assert r["total_survivors"] == 4
    assert r["counts"] == {"not_covered": 1, "survived_weak_oracle": 1,
                           "survived_maybe_equivalent": 1, "survived_unclassified": 1}
    assert r["advisory"] is True


def test_empty_or_none_is_zero():
    assert classify_survivors(None)["total_survivors"] == 0
    assert classify_survivors([])["counts"]["not_covered"] == 0


def test_matches_commons_cli_validate_real_finding():
    # docs/46 §16 real data: the two non-killed validate() mutants classify as the human did.
    rows = [
        {"line": 125, "method": "validate", "status": "NO_COVERAGE",
         "mutator": "EmptyObjectReturnValsMutator", "detected": False},
        {"line": 136, "method": "validate", "status": "SURVIVED",
         "mutator": "ConditionalsBoundaryMutator", "detected": False},
    ]
    cats = {s["line"]: s["category"] for s in classify_survivors(rows)["survivors"]}
    assert cats[125] == "not_covered"                 # validate(null) untested -> coverage gap
    assert cats[136] == "survived_maybe_equivalent"   # >->= equivalent -> review, not condemned


def test_report_md_renders_survivor_section_when_present_else_omits():
    from app.benchmark.models import BenchCaseResult, BenchReport, aggregate
    from app.benchmark.report_md import render_markdown

    surv = classify_survivors([
        {"line": 1, "method": "m", "status": "SURVIVED", "mutator": "MathMutator", "detected": False},
    ])
    case = BenchCaseResult(name="c", repo_url="u", target_class="C", conclusion="NEED_HUMAN_REVIEW",
                           review_summary={"mutation_survivors": surv})
    md = render_markdown(BenchReport(cases=[case], aggregate=aggregate([case])))
    assert "Survived mutants" in md and "survived_weak_oracle" in md
    # omitted entirely when no mutation rows (gated off)
    bare = BenchCaseResult(name="c", repo_url="u", target_class="C", conclusion="NEED_HUMAN_REVIEW")
    md2 = render_markdown(BenchReport(cases=[bare], aggregate=aggregate([bare])))
    assert "Survived mutants" not in md2
