"""Real-world validation-line metrics (docs/56). Offline and pure."""

from app.benchmark.models import BenchCaseResult, aggregate
from app.benchmark.validation_line import validation_line_summary


def _case(name: str, **overrides) -> BenchCaseResult:
    base = {
        "name": name,
        "repo_url": "https://example.test/repo.git",
        "target_class": "com.example.Calc",
        "repo_judged": True,
        "generation_status": "GEN_DONE",
        "gen_outcome": "PASS",
        "compiled": True,
        "executed": True,
        "passed": True,
        "quality_gate_status": "PASS",
        "quality_blockers": 0,
        "quality_warnings": 0,
        "conclusion": "NEED_HUMAN_REVIEW",
        "run_kind": "real",
        "review_summary": {
            "quality": {"status": "PASS", "blockers": [], "warnings": []},
            "oracle_strength_estimate": {"oracle_strength": "structural_ok"},
        },
    }
    base.update(overrides)
    return BenchCaseResult(**base)


def test_validation_line_v1_filters_run_kind_and_excludes_repaired_first_run():
    cases = [
        _case("real_pass"),
        _case(
            "real_compile_fail_weak",
            gen_outcome="COMPILE_FAILURE",
            compiled=False,
            executed=False,
            passed=False,
            failure_type="COMPILE_FAILURE",
            quality_gate_status="FAIL",
            quality_blockers=1,
            review_summary={
                "quality": {
                    "status": "FAIL",
                    "blockers": ["no_assertions"],
                    "warnings": [],
                },
                "oracle_strength_estimate": {"oracle_strength": "none"},
            },
        ),
        _case("real_repaired_final_pass", repair_rounds=1),
        _case(
            "real_preflight_reject",
            gen_outcome="COMPILE_FAILURE",
            compiled=False,
            executed=False,
            passed=False,
            failure_type="COMPILE_FAILURE",
            quality_gate_status="FAIL",
            quality_blockers=1,
            review_summary={
                "quality": {"status": "FAIL", "blockers": [], "warnings": []},
                "preflight": {"status": "FAIL", "blockers": [{"code": "bad_call"}]},
            },
        ),
        _case("fake_pass", run_kind="fake"),
        _case("historical_unknown", run_kind=None),
    ]

    raw = validation_line_summary(cases)
    real = validation_line_summary(cases, run_kind="real")

    assert raw["total_cases"] == 6
    assert raw["first_run_evidence_cases"] == 5
    assert raw["first_compile_pass_rate"] == 0.6
    assert raw["first_test_pass_rate"] == 0.6

    assert real["run_kind_filter"] == "real"
    assert real["total_cases"] == 4
    assert real["generation_attempted"] == 4
    assert real["first_run_evidence_cases"] == 3
    assert real["first_run_ambiguous_due_to_repair"] == 1
    assert real["preflight_reject_cases"] == 1
    assert real["first_compile_pass_count"] == 1
    assert real["first_compile_pass_rate"] == 0.3333
    assert real["first_test_pass_count"] == 1
    assert real["first_test_pass_rate"] == 0.3333
    assert real["structural_weak_signal_cases"] == 1
    assert real["structural_weak_signal_rate"] == 0.3333


def test_validation_line_structural_weak_signal_uses_oracle_and_mutation_hints():
    cases = [
        _case(
            "weak_oracle",
            oracle_strength="weak",
            review_summary={"quality": {"status": "PASS", "blockers": [], "warnings": []}},
        ),
        _case(
            "survived_weak_oracle",
            review_summary={
                "quality": {"status": "PASS", "blockers": [], "warnings": []},
                "mutation_survivors": {
                    "counts": {"survived_weak_oracle": 2},
                },
            },
        ),
        _case("clean"),
    ]

    summary = validation_line_summary(cases, run_kind="real")

    assert summary["structural_weak_signal_evaluated_cases"] == 3
    assert summary["structural_weak_signal_cases"] == 2
    assert summary["structural_weak_signal_rate"] == 0.6667


def test_validation_line_marks_human_and_golden_metrics_unavailable():
    summary = validation_line_summary([_case("a")], run_kind="real")

    unavailable = summary["human_or_golden_metrics"]
    assert unavailable["usable_test_rate"] == {
        "value": None,
        "status": "requires_human_disposition_labels",
    }
    assert unavailable["defect_discovery_rate"]["value"] is None
    assert unavailable["misjudgment_rate"]["status"] == (
        "requires_human_or_golden_reference_labels"
    )


def test_validation_line_does_not_change_aggregate_headline_shape():
    cases = [_case("a"), _case("b", run_kind="fake")]
    before_keys = set(aggregate(cases).keys())

    validation_line_summary(cases)

    assert set(aggregate(cases).keys()) == before_keys
    assert "first_compile_pass_rate" not in aggregate(cases)
