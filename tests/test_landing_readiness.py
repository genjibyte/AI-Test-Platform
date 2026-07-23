"""Landing-readiness rollup tests."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.benchmark.manifest_governance import GOLDEN_MANIFEST_SEED_SCHEMA_VERSION
from app.governance import (
    LANDING_READINESS_BLOCKER_SUMMARY_VERSION,
    LANDING_READINESS_SNAPSHOT_VERSION,
    LandingReadinessBlockerSummaryValidationError,
    LandingReadinessSnapshotValidationError,
    landing_readiness_blocker_summary,
    landing_readiness_snapshot,
    validate_landing_readiness_blocker_summary,
    validate_landing_readiness_snapshot,
)


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


def _seed(**overrides):
    seed = {
        "schema_version": GOLDEN_MANIFEST_SEED_SCHEMA_VERSION,
        "asset_id": "defects4j-chart-1",
        "intake_shape": "manifest_seed",
        "project_artifact": "benchmarks/manifest.golden.draft.json",
        "source_url": "https://github.com/rjust/defects4j",
        "pinned_version_or_commit": "v3.0.1",
        "license_spdx": "MIT",
        "license_verified_at": "2026-07-21",
        "runtime_language": "Java/Perl",
        "task_count_requested": 2,
        "task_ids": ["Chart-1", "Math-2"],
        "candidate_kind": "junit_unit_candidate",
        "expected_evidence": [
            "pinned bug id",
            "bug-revealing verifier metadata",
        ],
        "requires_network": False,
        "requires_docker": False,
        "requires_model_or_api_key": False,
        "red_lines": [
            "no bulk import",
            "no external execution without owner gate",
            "no headline metric",
        ],
        "next_action": "record metadata only",
    }
    seed.update(overrides)
    return seed


def test_landing_readiness_snapshot_marks_empty_inputs_as_pre_80():
    snapshot = landing_readiness_snapshot()

    assert snapshot["schema_version"] == LANDING_READINESS_SNAPSHOT_VERSION
    assert snapshot["advisory"] is True
    assert snapshot["report_only"] is True
    assert snapshot["overall_completion_percent"] == 71
    assert snapshot["landing_stage"] == "pre_80_landing_readiness_gaps"
    assert snapshot["ready_for_80_stage"] is False
    assert snapshot["ready_for_landing_claims"] is False
    assert snapshot["inputs"] == {
        "human_label_rows": 0,
        "human_reviewed_rows": 0,
        "golden_manifest_seed_records": 0,
    }
    assert "project_completion_below_80" in snapshot["landing_blockers"]
    assert "human_label:human_disposition_labels_missing" in (
        snapshot["landing_blockers"]
    )
    assert "golden_defect_denominator:no_defect_denominator_manifest_seed" in (
        snapshot["landing_blockers"]
    )
    assert snapshot["review_questions"][0]["id"] == "api_interface_boundary_review"
    assert snapshot["review_questions"][0]["authority"] == "planning_only"
    checklist = {item["id"]: item for item in snapshot["evidence_checklist"]}
    assert checklist["project_progress_at_least_80"]["current_status"] == "missing"
    assert checklist["human_disposition_labels"]["current_status"] == (
        "requires_human_disposition_labels"
    )
    assert checklist["pinned_defect_denominator"]["current_status"] == "missing"


def test_landing_readiness_rolls_up_supplied_labels_and_defect_seeds():
    snapshot = landing_readiness_snapshot(
        labels_or_projections=[
            _human_label(),
            _human_label(
                record_ref="bench:case-2",
                disposition="kept_with_edits",
                disposition_reason="kept after assertion rewrite",
                manual_revision_count=1,
                manual_revision_kinds=["assertion"],
                review_completed_at="2026-07-23T10:10:00Z",
            ),
        ],
        golden_manifest_seeds=[_seed()],
    )

    assert snapshot["human_ready_metric_names"] == [
        "usable_test_rate",
        "human_edit_count",
        "human_handling_time",
        "misjudgment_rate",
    ]
    assert snapshot["human_ready_metric_count"] == 4
    assert snapshot["future_defect_denominator_possible"] is True
    assert snapshot["defect_denominator_ready_now"] is False
    assert "golden_defect_denominator:dataset_slice_materialization_owner_gate_required" in (
        snapshot["landing_blockers"]
    )
    assert "golden_defect_denominator:verifier_execution_not_live" in (
        snapshot["landing_blockers"]
    )
    assert snapshot["human_label_readiness"]["headline_metric_authority"] is False
    assert snapshot["golden_defect_denominator_readiness"][
        "benchmark_headline_allowed_now"
    ] is False
    questions = {item["id"]: item for item in snapshot["review_questions"]}
    assert questions["human_label_calibration_review"]["authority"] == "planning_only"
    assert questions["golden_denominator_owner_gate_review"][
        "owner_decision_required"
    ] is True
    checklist = {item["id"]: item for item in snapshot["evidence_checklist"]}
    assert checklist["human_disposition_labels"]["current_status"] == "present"
    assert checklist["human_review_timestamps"]["current_status"] == "present"
    assert checklist["pinned_defect_denominator"]["current_status"] == (
        "future_owner_gated"
    )


def test_landing_readiness_snapshot_preserves_all_no_authority_flags():
    snapshot = landing_readiness_snapshot(
        progress_overrides={
            "api_interface_candidate_evaluation": 80,
            "real_world_validation_and_golden_set": 70,
        },
    )

    for field in (
        "runtime_authority",
        "executor_authority",
        "dependency_install_allowed",
        "pom_mutation_allowed",
        "external_execution_allowed",
        "dataset_materialization_allowed",
        "verifier_execution_allowed",
        "model_call_allowed",
        "persistence_authority",
        "headline_metric_authority",
        "git_stage_commit_push_authority",
        "digest_authority",
        "recommendation_authority",
        "verdict_authority",
        "trusted_authority",
    ):
        assert snapshot[field] is False

    assert snapshot["progress"]["overall_completion_percent"] == 77
    assert snapshot["ready_for_landing_claims"] is False
    assert all(item["authority"] != "verdict" for item in snapshot["review_questions"])


def test_validate_landing_readiness_snapshot_accepts_generated_snapshot():
    snapshot = landing_readiness_snapshot(
        labels_or_projections=[_human_label()],
        golden_manifest_seeds=[_seed()],
    )

    normalized = validate_landing_readiness_snapshot(snapshot)

    assert normalized["schema_version"] == LANDING_READINESS_SNAPSHOT_VERSION
    assert normalized["headline_metric_authority"] is False
    assert normalized["human_label_readiness"]["headline_metric_authority"] is False
    assert normalized["golden_defect_denominator_readiness"][
        "benchmark_headline_allowed_now"
    ] is False


def test_landing_readiness_blocker_summary_groups_current_blockers():
    snapshot = landing_readiness_snapshot()

    summary = landing_readiness_blocker_summary(snapshot)

    assert summary["schema_version"] == LANDING_READINESS_BLOCKER_SUMMARY_VERSION
    assert summary["advisory"] is True
    assert summary["report_only"] is True
    assert summary["source_schema_version"] == LANDING_READINESS_SNAPSHOT_VERSION
    assert summary["landing_stage"] == "pre_80_landing_readiness_gaps"
    assert summary["ready_for_landing_claims"] is False
    assert summary["total_blockers"] == len(snapshot["landing_blockers"])
    assert summary["family_counts"]["project_progress"] == 1
    assert summary["family_counts"]["human_label"] == 5
    assert summary["family_counts"]["golden_defect_denominator"] == 2
    assert summary["family_counts"]["change_batch"] == 0
    assert summary["next_clearance_family"] == "project_progress"

    families = {item["family"]: item for item in summary["families"]}
    assert families["project_progress"]["clearance_status"] == "blocked"
    assert families["project_progress"]["review_question_ids"] == [
        "api_interface_boundary_review"
    ]
    assert families["human_label"]["non_present_evidence_item_ids"] == [
        "human_disposition_labels",
        "human_review_timestamps",
        "human_or_verifier_rca",
        "misjudgment_reference_labels",
    ]
    assert families["golden_defect_denominator"][
        "non_present_evidence_item_ids"
    ] == ["pinned_defect_denominator"]
    assert families["change_batch"]["clearance_status"] == "human_review_required"
    assert summary["headline_metric_authority"] is False
    assert summary["dataset_materialization_allowed"] is False
    assert summary["verdict_authority"] is False
    assert summary["trusted_authority"] is False


def test_validate_landing_readiness_blocker_summary_accepts_generated_summary():
    summary = landing_readiness_blocker_summary(landing_readiness_snapshot())

    normalized = validate_landing_readiness_blocker_summary(summary)

    assert normalized["schema_version"] == LANDING_READINESS_BLOCKER_SUMMARY_VERSION
    assert normalized["source_schema_version"] == LANDING_READINESS_SNAPSHOT_VERSION
    assert normalized["family_counts"]["human_label"] == 5
    assert normalized["next_clearance_family"] == "project_progress"
    assert normalized["ready_for_landing_claims"] is False
    assert normalized["headline_metric_authority"] is False
    assert normalized["trusted_authority"] is False


@pytest.mark.parametrize(
    "mutate, match",
    [
        (
            lambda summary: summary.update({"headline_metric_authority": True}),
            "headline_metric_authority",
        ),
        (
            lambda summary: summary.update({"ready_for_landing_claims": True}),
            "must not approve landing claims",
        ),
        (
            lambda summary: summary["family_counts"].update({"human_label": 99}),
            "family_counts.human_label must match family blocker_count",
        ),
        (
            lambda summary: summary.update({"total_blockers": 99}),
            "total_blockers must match sum of family blocker counts",
        ),
        (
            lambda summary: summary["families"][0].update({
                "clearance_status": "evidence_present",
            }),
            "clearance_status must match blockers and evidence",
        ),
        (
            lambda summary: summary.update({"next_clearance_family": "human_label"}),
            "next_clearance_family must identify the first actionable family",
        ),
        (
            lambda summary: summary["families"][1][
                "non_present_evidence_item_ids"
            ].append("invented_evidence"),
            "non_present_evidence_item_ids must be a subset",
        ),
    ],
)
def test_validate_landing_readiness_blocker_summary_rejects_drift(
    mutate,
    match,
):
    summary = deepcopy(landing_readiness_blocker_summary(landing_readiness_snapshot()))
    mutate(summary)

    with pytest.raises(
        LandingReadinessBlockerSummaryValidationError,
        match=match,
    ):
        validate_landing_readiness_blocker_summary(summary)


def test_landing_readiness_blocker_summary_uses_validated_snapshot_boundary():
    snapshot = landing_readiness_snapshot()
    snapshot["landing_blockers"].append("human_label:invented_blocker")

    with pytest.raises(
        LandingReadinessSnapshotValidationError,
        match="landing_blockers must match progress",
    ):
        landing_readiness_blocker_summary(snapshot)


def test_validate_landing_readiness_snapshot_rejects_authority_drift():
    snapshot = landing_readiness_snapshot()
    snapshot["headline_metric_authority"] = True

    with pytest.raises(
        LandingReadinessSnapshotValidationError,
        match="headline_metric_authority",
    ):
        validate_landing_readiness_snapshot(snapshot)


def test_validate_landing_readiness_snapshot_rejects_malformed_review_aids():
    snapshot = landing_readiness_snapshot()
    snapshot["review_questions"][0]["authority"] = "verdict"

    with pytest.raises(
        LandingReadinessSnapshotValidationError,
        match="review_questions\\[0\\].authority",
    ):
        validate_landing_readiness_snapshot(snapshot)

    snapshot = landing_readiness_snapshot()
    del snapshot["evidence_checklist"][0]["required_evidence"]

    with pytest.raises(
        LandingReadinessSnapshotValidationError,
        match="evidence_checklist\\[0\\] missing required_evidence",
    ):
        validate_landing_readiness_snapshot(snapshot)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (
            lambda snapshot: snapshot.update({"overall_completion_percent": 101}),
            "overall_completion_percent must be between 0 and 100",
        ),
        (
            lambda snapshot: snapshot.update({"ready_for_80_stage": "false"}),
            "ready_for_80_stage must be a boolean",
        ),
        (
            lambda snapshot: snapshot.update({"landing_stage": "release_ready"}),
            "landing_stage is not allowed",
        ),
        (
            lambda snapshot: snapshot["source_versions"].update({
                "project_progress": "forged.v1",
            }),
            "source_versions.project_progress must match nested schema_version",
        ),
        (
            lambda snapshot: snapshot["inputs"].update({
                "human_label_rows": -1,
            }),
            "inputs.human_label_rows must be a non-negative integer",
        ),
        (
            lambda snapshot: snapshot.update({"human_ready_metric_count": 99}),
            "human_ready_metric_count must match human_ready_metric_names length",
        ),
        (
            lambda snapshot: snapshot["progress"].update({
                "overall_completion_percent": 72,
            }),
            "progress.overall_completion_percent must match top-level value",
        ),
    ],
)
def test_validate_landing_readiness_snapshot_rejects_typed_field_drift(
    mutate,
    match,
):
    snapshot = landing_readiness_snapshot()
    mutate(snapshot)

    with pytest.raises(LandingReadinessSnapshotValidationError, match=match):
        validate_landing_readiness_snapshot(snapshot)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (
            lambda snapshot: snapshot.update({
                "landing_stage": "landing_evidence_review_ready",
            }),
            "landing_stage must match percent and blockers",
        ),
        (
            lambda snapshot: snapshot.update({"ready_for_80_stage": True}),
            "ready_for_80_stage must match percent and blockers",
        ),
        (
            lambda snapshot: snapshot["landing_blockers"].append(
                "human_label:invented_blocker"
            ),
            "landing_blockers must match progress, human label readiness",
        ),
        (
            lambda snapshot: snapshot["next_best_steps"].append(
                "start API executor immediately"
            ),
            "next_best_steps must match landing_blockers",
        ),
        (
            lambda snapshot: snapshot["inputs"].update({"human_label_rows": 99}),
            "inputs.human_label_rows must match human_label_readiness.total_label_rows",
        ),
        (
            lambda snapshot: snapshot["inputs"].update({
                "human_reviewed_rows": 99,
            }),
            (
                "inputs.human_reviewed_rows must match "
                "human_label_readiness.human_reviewed_rows"
            ),
        ),
        (
            lambda snapshot: snapshot["inputs"].update({
                "golden_manifest_seed_records": 99,
            }),
            (
                "inputs.golden_manifest_seed_records must match "
                "golden_defect_denominator_readiness.total_seed_records"
            ),
        ),
        (
            lambda snapshot: snapshot.update({
                "future_defect_denominator_possible": True,
            }),
            "future_defect_denominator_possible must match denominator readiness",
        ),
        (
            lambda snapshot: snapshot.update({"defect_denominator_ready_now": True}),
            "defect_denominator_ready_now must match denominator readiness",
        ),
        (
            lambda snapshot: snapshot["human_label_readiness"].update({
                "ready_metric_count": 99,
            }),
            (
                "human_ready_metric_count must match "
                "human_label_readiness.ready_metric_count"
            ),
        ),
    ],
)
def test_validate_landing_readiness_snapshot_rejects_derived_field_drift(
    mutate,
    match,
):
    snapshot = landing_readiness_snapshot()
    mutate(snapshot)

    with pytest.raises(LandingReadinessSnapshotValidationError, match=match):
        validate_landing_readiness_snapshot(snapshot)


def test_validate_landing_readiness_snapshot_rejects_review_question_drift():
    snapshot = landing_readiness_snapshot()
    snapshot["review_questions"] = [
        question
        for question in snapshot["review_questions"]
        if question["id"] != "change_batch_review"
    ]

    with pytest.raises(
        LandingReadinessSnapshotValidationError,
        match="review_questions must match landing_blockers",
    ):
        validate_landing_readiness_snapshot(snapshot)


def test_validate_landing_readiness_snapshot_rejects_evidence_checklist_drift():
    snapshot = landing_readiness_snapshot()
    checklist = {item["id"]: item for item in snapshot["evidence_checklist"]}
    checklist["human_disposition_labels"]["current_status"] = "present"

    with pytest.raises(
        LandingReadinessSnapshotValidationError,
        match="evidence_checklist must match landing readiness inputs",
    ):
        validate_landing_readiness_snapshot(snapshot)
