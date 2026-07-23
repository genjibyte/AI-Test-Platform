"""Project progress snapshot tests."""
from __future__ import annotations

import pytest

from app.governance.project_progress import (
    PROJECT_PROGRESS_SNAPSHOT_VERSION,
    ProjectProgressValidationError,
    project_progress_snapshot,
)


def test_project_progress_snapshot_states_current_overall_completion():
    snapshot = project_progress_snapshot()

    assert snapshot["schema_version"] == PROJECT_PROGRESS_SNAPSHOT_VERSION
    assert snapshot["advisory"] is True
    assert snapshot["report_only"] is True
    assert snapshot["overall_completion_percent"] == 71
    assert snapshot["completion_band"] == "around_70"
    assert snapshot["stage"] == "late_core_harness_hardening_pre_80"
    assert snapshot["confidence"] == "medium"
    assert "API/interface candidate evaluation" in snapshot["not_80_yet_because"][0]
    assert snapshot["next_best_steps"][0].startswith(
        "freeze S6 landing-readiness governance"
    )
    assert snapshot["next_best_steps"][1] == (
        "build one small joint human-label plus Golden Set evidence slice before stronger outcome metrics"
    )
    assert snapshot["next_best_steps"][2].startswith(
        "defer owner-gated API/interface implementation design"
    )


def test_project_progress_snapshot_preserves_no_authority_boundary():
    snapshot = project_progress_snapshot()

    for field in (
        "runtime_authority",
        "executor_authority",
        "dependency_install_allowed",
        "pom_mutation_allowed",
        "external_execution_allowed",
        "model_call_allowed",
        "git_stage_commit_push_authority",
        "digest_authority",
        "verdict_authority",
        "trusted_authority",
    ):
        assert snapshot[field] is False

    assert any(
        line == "do not change conclusion=NEED_HUMAN_REVIEW or trusted=False"
        for line in snapshot["red_lines"]
    )
    assert any(
        "do not continue S6R/S6S-style governance hardening" in line
        for line in snapshot["red_lines"]
    )


def test_project_progress_snapshot_has_weighted_components():
    snapshot = project_progress_snapshot()
    components = {component["id"]: component for component in snapshot["components"]}

    assert sum(component["weight"] for component in components.values()) == 100
    assert components["judge_kernel_execution_evidence"]["completion_percent"] == 82
    assert components["api_interface_candidate_evaluation"]["completion_percent"] == 58
    assert components["real_world_validation_and_golden_set"]["completion_percent"] == 50
    assert components["producer_agnostic_candidate_entry"]["pillar"] == "Candidate"
    assert "API/interface implementation design is lower priority until the joint human+Golden evidence slice exists" in (
        components["api_interface_candidate_evaluation"]["remaining"]
    )
    assert "human labels and Golden Set denominator metadata must advance as one closure slice" in (
        components["real_world_validation_and_golden_set"]["remaining"]
    )
    assert components["governance_handoff_reuse_skill_readiness"]["status"] == (
        "metadata_governance_live_frozen_for_closure"
    )
    assert "landing readiness rollup, blocker-family summary/validator/Markdown, Markdown presentation, review checklist, typed boundary validator, and derived-consistency validator are metadata-only live" in (
        components["governance_handoff_reuse_skill_readiness"]["evidence"]
    )
    assert "S6 landing-readiness governance is frozen unless a real high-risk boundary bug appears" in (
        components["governance_handoff_reuse_skill_readiness"]["evidence"]
    )


def test_project_progress_snapshot_allows_bounded_scenario_overrides():
    snapshot = project_progress_snapshot({
        "api_interface_candidate_evaluation": 78,
        "real_world_validation_and_golden_set": 65,
    })

    assert snapshot["overall_completion_percent"] == 76
    assert snapshot["completion_band"] == "approaching_80"
    assert snapshot["stage"] == "late_core_harness_hardening_pre_80"
    assert snapshot["executor_authority"] is False


@pytest.mark.parametrize(
    "overrides, match",
    [
        ({"unknown": 70}, "unknown progress component"),
        ({"api_interface_candidate_evaluation": 101}, "between 0 and 100"),
        ({"api_interface_candidate_evaluation": -1}, "between 0 and 100"),
        ({"api_interface_candidate_evaluation": True}, "must be numeric"),
    ],
)
def test_project_progress_snapshot_rejects_invalid_overrides(overrides, match):
    with pytest.raises(ProjectProgressValidationError, match=match):
        project_progress_snapshot(overrides)
