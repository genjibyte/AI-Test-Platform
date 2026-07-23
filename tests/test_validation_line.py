"""Real-world validation-line metrics (docs/56). Offline and pure."""

from app.benchmark.models import BenchCaseResult, aggregate
from app.benchmark.validation_line import (
    HUMAN_LABEL_READINESS_VERSION,
    human_label_metric_readiness,
    validation_line_summary,
)


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


def _human_label(**overrides):
    label = {
        "record_ref": "bench:case-1",
        "candidate_ref": "job:1",
        "reviewer_ref": "reviewer:local",
        "review_started_at": "2026-07-23T10:00:00Z",
        "review_completed_at": "2026-07-23T10:05:00Z",
        "disposition": "kept",
        "disposition_reason": "usable as-is",
        "manual_revision_count": 0,
        "manual_revision_kinds": [],
        "misjudgment": {
            "kind": "none",
            "misled_human": False,
        },
    }
    label.update(overrides)
    return label


def test_human_label_metric_readiness_marks_empty_input_not_ready():
    summary = human_label_metric_readiness([])

    assert summary["schema_version"] == HUMAN_LABEL_READINESS_VERSION
    assert summary["advisory"] is True
    assert summary["report_only"] is True
    assert summary["total_label_rows"] == 0
    assert summary["metrics"]["usable_test_rate"] == {
        "status": "requires_human_disposition_labels",
        "denominator": 0,
        "numerator": 0,
        "value": None,
        "headline_allowed_now": False,
    }
    assert "human_disposition_labels_missing" in summary["not_ready_reasons"]
    assert summary["headline_metric_authority"] is False
    assert summary["verdict_authority"] is False
    assert summary["trusted_authority"] is False


def test_human_label_metric_readiness_projects_available_human_metrics():
    labels = [
        _human_label(),
        _human_label(
            record_ref="bench:case-2",
            disposition="kept_with_edits",
            disposition_reason="kept after assertion rewrite",
            manual_revision_count=2,
            manual_revision_kinds=["assertion"],
            review_completed_at="2026-07-23T10:10:00Z",
            root_cause={
                "family": "oracle",
                "code": "oracle_weak_or_missing",
                "confidence": "human_confirmed",
                "recorded_at": "2026-07-23T10:09:00Z",
                "evidence_refs": ["report.quality.blockers:no_assertions"],
            },
        ),
        _human_label(
            record_ref="bench:case-3",
            disposition="rejected",
            disposition_reason="candidate revealed a confirmed product bug",
            root_cause={
                "family": "product",
                "code": "product_bug_confirmed",
                "confidence": "verifier_confirmed",
                "recorded_at": "2026-07-23T10:04:00Z",
                "evidence_refs": ["verifier:defect-seed-1"],
            },
            misjudgment={
                "kind": "false_negative",
                "platform_signal": "review_digest",
                "human_verdict": "digest missed confirmed product-bug evidence",
                "misled_human": False,
            },
        ),
        {"record_ref": "bench:not-reviewed-yet"},
    ]

    summary = human_label_metric_readiness(labels)
    metrics = summary["metrics"]

    assert summary["total_label_rows"] == 4
    assert summary["human_reviewed_rows"] == 3
    assert metrics["usable_test_rate"]["denominator"] == 3
    assert metrics["usable_test_rate"]["numerator"] == 2
    assert metrics["usable_test_rate"]["value"] == 0.6667
    assert metrics["human_edit_count"]["average_manual_revision_count"] == 0.6667
    assert metrics["human_handling_time"]["average_seconds"] == 400
    assert metrics["misjudgment_rate"]["denominator"] == 3
    assert metrics["misjudgment_rate"]["numerator"] == 1
    assert metrics["misjudgment_rate"]["value"] == 0.3333
    assert metrics["defect_discovery_rate"]["defect_discovery_label_count"] == 1
    assert metrics["defect_discovery_rate"]["value"] is None
    assert "pinned_defect_denominator_missing" in summary["not_ready_reasons"]
    assert summary["headline_metric_authority"] is False


def test_human_label_metric_readiness_accepts_existing_metric_projections():
    projection = {
        "schema_version": "human_review_metric_projection.v1",
        "human_reviewed": True,
        "disposition": "kept",
        "usable_test": True,
        "manual_revision_count": 0,
        "manual_revision_kinds": [],
        "human_handling_time_seconds": 300,
        "root_cause_recorded": False,
        "defect_discovery_label": False,
        "misjudgment_kind": "none",
        "advisory_only": True,
        "conclusion": "NEED_HUMAN_REVIEW",
        "trusted": False,
    }

    summary = human_label_metric_readiness([projection])

    assert summary["metrics"]["usable_test_rate"]["value"] == 1.0
    assert summary["metrics"]["human_handling_time"]["average_seconds"] == 300
