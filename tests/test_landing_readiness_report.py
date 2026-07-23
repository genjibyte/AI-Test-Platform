"""Landing-readiness Markdown presentation tests."""
from __future__ import annotations

import pytest

from app.benchmark.manifest_governance import GOLDEN_MANIFEST_SEED_SCHEMA_VERSION
from app.governance import (
    LandingReadinessBlockerSummaryValidationError,
    LandingReadinessSnapshotValidationError,
    landing_readiness_blocker_summary,
    landing_readiness_snapshot,
    render_landing_readiness_blocker_summary_markdown,
    render_landing_readiness_markdown,
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


def test_render_landing_readiness_markdown_omits_absent_snapshots():
    assert render_landing_readiness_markdown({}) == ""
    assert render_landing_readiness_markdown({"schema_version": "other"}) == ""
    assert render_landing_readiness_markdown(None) == ""


def test_render_landing_readiness_markdown_is_presentation_only():
    snapshot = landing_readiness_snapshot(
        labels_or_projections=[_human_label()],
        golden_manifest_seeds=[_seed()],
    )

    md = render_landing_readiness_markdown(snapshot)

    assert "## Landing readiness - PLANNING SNAPSHOT" in md
    assert "schema_version: landing_readiness_snapshot.v1" in md
    assert "overall_completion_percent: 71" in md
    assert "landing_stage: pre_80_landing_readiness_gaps" in md
    assert "ready_for_80_stage: False" in md
    assert "ready_for_landing_claims: False" in md
    assert "human_label_rows=1" in md
    assert "human_ready_metric_names: usable_test_rate" in md
    assert "future_possible=True  ready_now=False" in md
    assert "headline_metric_authority=False" in md
    assert "dataset_materialization_allowed=False" in md
    assert "verifier_execution_allowed=False" in md
    assert "verdict_authority=False" in md
    assert "trusted_authority=False" in md
    assert "no release, headline, dataset, verifier, verdict, or trust authority" in md
    assert "project_completion_below_80" in md
    assert "golden_defect_denominator:verifier_execution_not_live" in md
    assert "supply calibrated human-review labels" in md
    assert "| blocker_family | blocker_count | clearance_status |" in md
    assert "| project_progress | 1 | blocked | api_interface_boundary_review |" in md
    assert "| change_batch | 0 | human_review_required | change_batch_review |" in md
    assert "| review_question | triggered_by | authority |" in md
    assert "Which API/interface evidence boundary must stabilize" in md
    assert "planning_only" in md
    assert "| evidence_item | current_status | required_evidence | authority |" in md
    assert "| project_progress_at_least_80 | missing |" in md
    assert "| human_disposition_labels | present |" in md
    assert "| pinned_defect_denominator | future_owner_gated |" in md
    assert "release approved" not in md
    assert "trusted=True" not in md


def test_render_landing_readiness_markdown_escapes_table_cells():
    snapshot = landing_readiness_snapshot()
    snapshot["human_label_readiness"]["not_ready_reasons"] = ["needs|review"]
    snapshot["human_label_readiness"]["metrics"]["usable_test_rate"][
        "status"
    ] = "needs|review"
    snapshot["landing_blockers"] = [
        "project_completion_below_80",
        "human_label:needs|review",
        "golden_defect_denominator:no_defect_denominator_manifest_seed",
        "golden_defect_denominator:not_ready_now",
    ]
    snapshot["review_questions"] = [
        {
            "id": "api_interface_boundary_review",
            "question": "Which API/interface evidence boundary must stabilize?",
            "triggered_by": ["project_completion_below_80"],
            "owner_decision_required": True,
            "authority": "planning_only",
        },
        {
            "id": "human_label_calibration_review",
            "question": "question|one",
            "triggered_by": ["human_label:needs|review"],
            "owner_decision_required": True,
            "authority": "planning_only",
        },
        {
            "id": "golden_denominator_owner_gate_review",
            "question": "Which manifest_seed records have pinned defect tasks?",
            "triggered_by": [
                "golden_defect_denominator:no_defect_denominator_manifest_seed",
                "golden_defect_denominator:not_ready_now",
            ],
            "owner_decision_required": True,
            "authority": "planning_only",
        },
        {
            "id": "change_batch_review",
            "question": "Which current change-set batch needs review?",
            "triggered_by": ["large_dirty_worktree"],
            "owner_decision_required": True,
            "authority": "handoff_only",
        },
    ]
    checklist = {item["id"]: item for item in snapshot["evidence_checklist"]}
    checklist["human_disposition_labels"]["current_status"] = "needs|review"
    checklist["human_disposition_labels"]["required_evidence"] = "line\nbreak"

    md = render_landing_readiness_markdown(snapshot)

    assert "| human_label:needs/review |" in md
    assert "| question/one | human_label:needs/review | planning_only |" in md
    assert "| human_disposition_labels | needs/review | line break |" in md


def test_render_landing_readiness_markdown_rejects_v1_authority_drift():
    snapshot = landing_readiness_snapshot()
    snapshot["golden_defect_denominator_readiness"][
        "benchmark_headline_allowed_now"
    ] = True

    with pytest.raises(
        LandingReadinessSnapshotValidationError,
        match="benchmark_headline_allowed_now",
    ):
        render_landing_readiness_markdown(snapshot)


def test_render_landing_readiness_blocker_summary_markdown_omits_absent_summaries():
    assert render_landing_readiness_blocker_summary_markdown({}) == ""
    assert render_landing_readiness_blocker_summary_markdown({
        "schema_version": "other",
    }) == ""
    assert render_landing_readiness_blocker_summary_markdown(None) == ""


def test_render_landing_readiness_blocker_summary_markdown_is_presentation_only():
    summary = landing_readiness_blocker_summary(landing_readiness_snapshot())

    md = render_landing_readiness_blocker_summary_markdown(summary)

    assert "## Landing readiness blocker summary - PLANNING VIEW" in md
    assert "schema_version: landing_readiness_blocker_summary.v1" in md
    assert "source_schema_version: landing_readiness_snapshot.v1" in md
    assert "landing_stage: pre_80_landing_readiness_gaps" in md
    assert "ready_for_80_stage: False" in md
    assert "ready_for_landing_claims: False" in md
    assert "total_blockers: 8" in md
    assert "next_clearance_family: project_progress" in md
    assert "headline_metric_authority=False" in md
    assert "dataset_materialization_allowed=False" in md
    assert "verdict_authority=False" in md
    assert "trusted_authority=False" in md
    assert "| blocker_family | blocker_count | clearance_status |" in md
    assert "| project_progress | 1 | blocked | api_interface_boundary_review |" in md
    assert "| human_label | 5 | blocked | human_label_calibration_review |" in md
    assert "| change_batch | 0 | human_review_required | change_batch_review |" in md
    assert "release approved" not in md
    assert "trusted=True" not in md


def test_render_landing_readiness_blocker_summary_markdown_rejects_drift():
    summary = landing_readiness_blocker_summary(landing_readiness_snapshot())
    summary["families"][0]["clearance_status"] = "evidence_present"

    with pytest.raises(
        LandingReadinessBlockerSummaryValidationError,
        match="clearance_status must match blockers and evidence",
    ):
        render_landing_readiness_blocker_summary_markdown(summary)
