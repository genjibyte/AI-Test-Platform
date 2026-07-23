"""CI/PR change-handoff governance tests."""
from __future__ import annotations

import pytest

from app.governance import (
    CHANGE_HANDOFF_PLAN_VERSION,
    ChangeHandoffValidationError,
    change_handoff_plan,
    parse_git_status_short,
    render_change_handoff_markdown,
)


def test_parse_git_status_short_normalizes_common_rows():
    changes = parse_git_status_short([
        " M app/report/generation_report.py",
        "D  docs/10_phase1/05_PHASE1_BACKLOG.md",
        "?? app/governance/change_handoff.py",
        "R  old.md -> docs/README.md",
    ])

    assert changes == [
        {
            "path": "app/report/generation_report.py",
            "status": "modified",
            "raw_status": " M",
        },
        {
            "path": "docs/10_phase1/05_PHASE1_BACKLOG.md",
            "status": "deleted",
            "raw_status": "D ",
        },
        {
            "path": "app/governance/change_handoff.py",
            "status": "untracked",
            "raw_status": "??",
        },
        {
            "path": "docs/README.md",
            "status": "renamed",
            "raw_status": "R ",
            "old_path": "old.md",
        },
    ]


def test_change_handoff_plan_groups_current_project_surfaces():
    changes = parse_git_status_short([
        " M app/report/generation_report.py",
        "?? app/report/api_smoke_manifest.py",
        "?? app/governance/external_assets.py",
        "?? app/benchmark/manifest_governance.py",
        " M README.md",
        "D  docs/20_phase2/09_PHASE2_BACKLOG.md",
        " M tests/test_submit_candidate.py",
    ])

    plan = change_handoff_plan(
        changes,
        verification=[
            {
                "command": "& .venv/Scripts/python.exe -m pytest",
                "result": "609 passed, 4 skipped, 1 warning",
                "passed": True,
            }
        ],
        branch="main",
        unpushed_commits=0,
        staged=False,
        dirty=True,
    )

    assert plan["plan_version"] == CHANGE_HANDOFF_PLAN_VERSION
    assert plan["advisory"] is True
    assert plan["handoff_only"] is True
    assert plan["push_allowed_for_agent"] is False
    assert plan["merge_allowed_for_agent"] is False
    assert plan["verdict_authority"] is False
    assert plan["trusted_authority"] is False
    assert plan["verification_passed"] is True
    assert plan["ready_for_human_handoff"] is True
    assert plan["by_surface"] == {
        "api_smoke_report_projection": 3,
        "external_asset_governance": 1,
        "golden_manifest_governance": 1,
        "root_handoff_docs": 1,
        "docs_prune": 1,
    }
    assert "docs_prune_requires_owner_awareness" in plan["warning_flags"]
    assert "dirty_worktree_not_staged" in plan["warning_flags"]

    groups = {group["name"]: group for group in plan["commit_groups"]}
    assert groups["docs_prune"]["recommended_action"] == "keep_with_owner_awareness"
    assert groups["api_smoke_report_projection"]["recommended_action"] == "keep"
    assert groups["api_smoke_report_projection"]["status_counts"] == {
        "modified": 2,
        "untracked": 1,
    }
    assert groups["api_smoke_report_projection"]["paths_by_status"] == {
        "modified": [
            "app/report/generation_report.py",
            "tests/test_submit_candidate.py",
        ],
        "untracked": ["app/report/api_smoke_manifest.py"],
    }
    assert groups["golden_manifest_governance"]["recommended_action"] == "keep"

    batches = {batch["name"]: batch for batch in plan["commit_batches"]}
    assert list(batches) == [
        "api_smoke_report_projection",
        "governance_helpers",
        "active_docs_and_handoff_context",
        "historical_docs_prune",
    ]
    assert batches["api_smoke_report_projection"]["recommended_action"] == "keep"
    assert batches["api_smoke_report_projection"]["commit_message_hint"] == (
        "Add API smoke report projection carry"
    )
    assert "red-line descriptive counts" in " ".join(
        batches["api_smoke_report_projection"]["notes"]
    )
    assert "no executor" in " ".join(
        batches["api_smoke_report_projection"]["review_checklist"]
    )
    assert batches["api_smoke_report_projection"]["review_gates"] == [
        "human_review_required",
        "verification_required",
        "no_executor_or_verdict_drift",
    ]
    assert batches["api_smoke_report_projection"]["status_counts"] == {
        "modified": 2,
        "untracked": 1,
    }
    assert batches["api_smoke_report_projection"]["paths_by_status"] == {
        "modified": [
            "app/report/generation_report.py",
            "tests/test_submit_candidate.py",
        ],
        "untracked": ["app/report/api_smoke_manifest.py"],
    }
    assert batches["api_smoke_report_projection"]["surface_counts"] == {
        "api_smoke_report_projection": 3,
    }
    assert batches["api_smoke_report_projection"]["warning_flags"] == [
        "untracked_paths_present",
    ]
    assert batches["governance_helpers"]["status_counts"] == {"untracked": 2}
    assert batches["governance_helpers"]["surface_counts"] == {
        "external_asset_governance": 1,
        "golden_manifest_governance": 1,
    }
    assert batches["governance_helpers"]["warning_flags"] == [
        "untracked_paths_present",
    ]
    assert batches["governance_helpers"]["commit_message_hint"] == (
        "Add governance handoff helpers"
    )
    assert batches["active_docs_and_handoff_context"]["status_counts"] == {
        "modified": 1,
    }
    assert batches["active_docs_and_handoff_context"]["surface_counts"] == {
        "root_handoff_docs": 1,
    }
    assert batches["active_docs_and_handoff_context"]["commit_message_hint"] == (
        "Refresh active docs and handoff context"
    )
    assert batches["historical_docs_prune"]["status_counts"] == {"deleted": 1}
    assert batches["historical_docs_prune"]["paths_by_status"] == {
        "deleted": ["docs/20_phase2/09_PHASE2_BACKLOG.md"],
    }
    assert batches["historical_docs_prune"]["surface_counts"] == {
        "docs_prune": 1,
    }
    assert batches["historical_docs_prune"]["warning_flags"] == [
        "docs_prune_requires_owner_awareness",
    ]
    assert batches["historical_docs_prune"]["commit_message_hint"] == (
        "Prune historical docs from active tree"
    )
    assert batches["api_smoke_report_projection"]["verification_targets"][0] == {
        "command": (
            "pytest tests/test_api_smoke_projection_boundary.py "
            "tests/test_api_smoke_benchmark_projection.py "
            "tests/test_benchmark.py tests/test_api_smoke_ledger_projection.py"
        ),
        "purpose": "API smoke benchmark and ledger projection presentation",
    }
    assert "tests/test_change_handoff.py" in (
        batches["governance_helpers"]["verification_targets"][0]["command"]
    )
    assert plan["review_gate_counts"]["human_review_required"] == 3
    assert plan["review_gate_counts"]["verification_required"] == 2
    assert plan["review_gate_counts"]["owner_awareness_required"] == 1
    assert plan["batch_action_counts"] == {
        "keep": 3,
        "keep_with_owner_awareness": 1,
    }
    assert plan["batch_warning_counts"] == {
        "untracked_paths_present": 2,
        "docs_prune_requires_owner_awareness": 1,
    }
    assert plan["verification_target_counts"] == {
        "api_smoke_report_projection": 2,
        "governance_helpers": 2,
        "active_docs_and_handoff_context": 2,
        "historical_docs_prune": 1,
    }
    assert plan["human_next_actions"] == [
        "review untracked paths in each keep batch before staging",
        "confirm owner awareness before staging docs-prune batch",
        "rerun suggested verification targets for each batch before commit",
        "human may stage reviewed batches separately; agent must not stage or push",
    ]
    assert batches["historical_docs_prune"]["recommended_action"] == (
        "keep_with_owner_awareness"
    )
    assert "git history" in " ".join(
        batches["historical_docs_prune"]["review_checklist"]
    )
    assert "owner_awareness_required" in batches["historical_docs_prune"]["review_gates"]


def test_change_handoff_batches_api_smoke_integration_files_together():
    changes = parse_git_status_short([
        " M app/benchmark/report_md.py",
        " M app/report/__init__.py",
        " M app/ledger/models.py",
        " M app/ledger/ingest.py",
        " M tests/test_ledger.py",
        "?? tests/test_api_smoke_projection_boundary.py",
        " M app/runtime_leftover.py",
    ])

    plan = change_handoff_plan(
        changes,
        verification=[
            {
                "command": "pytest tests/test_ledger.py tests/test_benchmark.py",
                "result": "ok",
                "passed": True,
            }
        ],
        unpushed_commits=0,
    )

    assert plan["by_surface"] == {
        "api_smoke_report_projection": 6,
        "runtime_code": 1,
    }
    assert plan["commit_batches"][0]["name"] == "api_smoke_report_projection"
    assert plan["commit_batches"][0]["paths"] == [
        "app/benchmark/report_md.py",
        "app/ledger/ingest.py",
        "app/ledger/models.py",
        "app/report/__init__.py",
        "tests/test_api_smoke_projection_boundary.py",
        "tests/test_ledger.py",
    ]
    assert plan["commit_batches"][-1]["name"] == "residual_runtime_and_tests"
    assert plan["commit_batches"][-1]["recommended_action"] == "review_before_keep"
    assert plan["commit_batches"][-1]["paths"] == ["app/runtime_leftover.py"]
    assert plan["commit_batches"][-1]["status_counts"] == {"modified": 1}
    assert plan["commit_batches"][-1]["warning_flags"] == ["review_before_keep"]
    assert plan["commit_batches"][-1]["commit_message_hint"] == (
        "Review residual runtime and test changes"
    )
    assert "residual_runtime_or_tests_need_review" in plan["warning_flags"]


def test_change_handoff_reclassifies_known_completed_track_leftovers():
    changes = parse_git_status_short([
        "?? app/governance/",
        " M app/governance/change_handoff.py",
        " M tests/test_change_handoff.py",
        " M docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md",
        " M tests/test_test_level_router.py",
        " M app/report/__init__.py",
    ])

    plan = change_handoff_plan(
        changes,
        verification=[
            {
                "command": "pytest tests/test_change_handoff.py",
                "result": "ok",
                "passed": True,
            }
        ],
        unpushed_commits=0,
    )

    assert plan["by_surface"] == {
        "handoff_governance": 3,
        "asset_gate_router_audit": 2,
        "api_smoke_report_projection": 1,
    }
    assert "residual_runtime_or_tests_need_review" not in plan["warning_flags"]

    batches = {batch["name"]: batch for batch in plan["commit_batches"]}
    assert batches["governance_helpers"]["paths"] == [
        "app/governance",
        "app/governance/change_handoff.py",
        "tests/test_change_handoff.py",
    ]
    assert batches["active_docs_and_handoff_context"]["paths"] == [
        "docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md",
        "tests/test_test_level_router.py",
    ]


def test_change_handoff_groups_skill_sop_governance_with_governance_helpers():
    changes = parse_git_status_short([
        "?? app/governance/skill_sop.py",
        " M docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md",
        "?? tests/test_judge_skill_sop.py",
    ])

    plan = change_handoff_plan(
        changes,
        verification=[
            {
                "command": "pytest tests/test_judge_skill_sop.py",
                "result": "ok",
                "passed": True,
            }
        ],
        unpushed_commits=0,
    )

    assert plan["by_surface"] == {"skill_sop_governance": 3}
    assert "residual_runtime_or_tests_need_review" not in plan["warning_flags"]

    batches = {batch["name"]: batch for batch in plan["commit_batches"]}
    assert batches["governance_helpers"]["surface_counts"] == {
        "skill_sop_governance": 3
    }
    assert batches["governance_helpers"]["paths"] == [
        "app/governance/skill_sop.py",
        "docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md",
        "tests/test_judge_skill_sop.py",
    ]
    assert "Skill/SOP readiness" in " ".join(
        batches["governance_helpers"]["notes"]
    )


def test_change_handoff_groups_java_framework_neutrality_as_keep_batch():
    changes = parse_git_status_short([
        "?? app/report/java_test_framework.py",
        "?? docs/60_api_candidate/10_JAVA_TEST_FRAMEWORK_NEUTRALITY.md",
        " M tests/test_generation_report.py",
        "?? tests/test_java_test_framework.py",
    ])

    plan = change_handoff_plan(
        changes,
        verification=[
            {
                "command": "pytest tests/test_java_test_framework.py",
                "result": "ok",
                "passed": True,
            }
        ],
        unpushed_commits=0,
    )

    assert plan["by_surface"] == {"java_framework_neutrality": 4}
    assert "residual_runtime_or_tests_need_review" not in plan["warning_flags"]

    batches = {batch["name"]: batch for batch in plan["commit_batches"]}
    assert batches["java_framework_neutrality"]["recommended_action"] == "keep"
    assert batches["java_framework_neutrality"]["surface_counts"] == {
        "java_framework_neutrality": 4
    }
    assert batches["java_framework_neutrality"]["paths"] == [
        "app/report/java_test_framework.py",
        "docs/60_api_candidate/10_JAVA_TEST_FRAMEWORK_NEUTRALITY.md",
        "tests/test_generation_report.py",
        "tests/test_java_test_framework.py",
    ]
    assert "TestNG is visible" in " ".join(
        batches["java_framework_neutrality"]["notes"]
    )


def test_change_handoff_groups_landing_readiness_snapshots_as_keep_batch():
    changes = parse_git_status_short([
        "?? app/governance/__init__.py",
        "?? app/governance/project_progress.py",
        "?? docs/00_foundation/63_PROJECT_PROGRESS_SNAPSHOT.md",
        "?? tests/test_project_progress.py",
        " M app/benchmark/__init__.py",
        " M app/benchmark/validation_line.py",
        " M app/review/human_labels.py",
        " M docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md",
        " M docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md",
        " M tests/test_human_labels.py",
        " M tests/test_validation_line.py",
    ])

    plan = change_handoff_plan(
        changes,
        verification=[
            {
                "command": (
                    "pytest tests/test_project_progress.py "
                    "tests/test_validation_line.py tests/test_human_labels.py"
                ),
                "result": "ok",
                "passed": True,
            }
        ],
        unpushed_commits=0,
    )

    assert plan["by_surface"] == {
        "project_progress_readiness": 4,
        "landing_validation_readiness": 7,
    }
    assert "residual_runtime_or_tests_need_review" not in plan["warning_flags"]

    batches = {batch["name"]: batch for batch in plan["commit_batches"]}
    assert batches["landing_readiness_snapshots"]["recommended_action"] == "keep"
    assert batches["landing_readiness_snapshots"]["surface_counts"] == {
        "project_progress_readiness": 4,
        "landing_validation_readiness": 7,
    }
    assert batches["landing_readiness_snapshots"]["status_counts"] == {
        "modified": 7,
        "untracked": 4,
    }
    assert batches["landing_readiness_snapshots"]["warning_flags"] == [
        "untracked_paths_present",
    ]
    assert batches["landing_readiness_snapshots"]["commit_message_hint"] == (
        "Add landing readiness snapshots"
    )
    assert "human/golden labels" in " ".join(
        batches["landing_readiness_snapshots"]["notes"]
    )
    assert "no_headline_or_verdict_authority" in (
        batches["landing_readiness_snapshots"]["review_gates"]
    )
    assert "tests/test_project_progress.py" in (
        batches["landing_readiness_snapshots"]["verification_targets"][0]["command"]
    )
    assert "tests/test_landing_readiness_report.py" in (
        batches["landing_readiness_snapshots"]["verification_targets"][0]["command"]
    )
    assert "tests/test_validation_line.py" in (
        batches["landing_readiness_snapshots"]["verification_targets"][0]["command"]
    )
    assert "tests/test_human_labels.py" in (
        batches["landing_readiness_snapshots"]["verification_targets"][0]["command"]
    )


def test_change_handoff_reclassifies_runtime_doc_reference_cleanup():
    changes = parse_git_status_short([
        " M app/__init__.py",
        " M app/benchmark/business_tags.py",
        " M app/main.py",
        " M tests/e2e/test_phase1_e2e.py",
    ])

    plan = change_handoff_plan(
        changes,
        verification=[
            {
                "command": "pytest tests/e2e/test_phase1_e2e.py",
                "result": "skipped unless TESTAGENT_E2E=1",
                "passed": True,
            }
        ],
        unpushed_commits=0,
    )

    assert plan["by_surface"] == {"runtime_doc_reference_cleanup": 4}
    assert "residual_runtime_or_tests_need_review" not in plan["warning_flags"]

    batches = {batch["name"]: batch for batch in plan["commit_batches"]}
    assert batches["active_docs_and_handoff_context"]["paths"] == [
        "app/__init__.py",
        "app/benchmark/business_tags.py",
        "app/main.py",
        "tests/e2e/test_phase1_e2e.py",
    ]
    assert "pruned docs" in " ".join(
        group["notes"][0]
        for group in plan["commit_groups"]
        if group["name"] == "runtime_doc_reference_cleanup"
    )


def test_change_handoff_plan_requires_command_evidence_for_readiness():
    plan = change_handoff_plan(
        [{"path": "README.md", "status": "modified"}],
        branch="main",
        unpushed_commits=0,
    )

    assert plan["verification_passed"] is False
    assert plan["ready_for_human_handoff"] is False
    assert plan["blocking_flags"] == ["verification_missing"]
    assert plan["human_next_actions"][0] == "resolve blocking flags before staging"


def test_change_handoff_plan_blocks_failed_verification_and_agent_push():
    plan = change_handoff_plan(
        [{"path": "README.md", "status": "modified"}],
        verification=[
            {
                "command": "pytest",
                "result": "1 failed",
                "passed": False,
            }
        ],
        branch="main",
        unpushed_commits=1,
        push_performed=True,
    )

    assert plan["ready_for_human_handoff"] is False
    assert plan["blocking_flags"] == [
        "push_already_performed_by_agent",
        "verification_failed",
    ]
    assert "unpushed_commits_present" in plan["warning_flags"]


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "config/.env.local",
        "secrets/prod.pem",
        "secrets/client.key",
        "../outside.txt",
        "C:/tmp/file.txt",
    ],
)
def test_change_handoff_rejects_secret_or_out_of_repo_paths(path):
    with pytest.raises(ChangeHandoffValidationError):
        change_handoff_plan([{"path": path, "status": "modified"}])


def test_render_change_handoff_markdown_is_handoff_only():
    plan = change_handoff_plan(
        [{"path": "app/governance/change_handoff.py", "status": "untracked"}],
        verification=[
            {
                "command": "pytest tests/test_change_handoff.py",
                "result": "6 passed",
                "passed": True,
            }
        ],
        branch="main",
        unpushed_commits=0,
        staged=True,
        dirty=True,
    )

    md = render_change_handoff_markdown(plan)

    assert "## CI/PR handoff - CHANGE SET" in md
    assert "### Suggested Commit Batches" in md
    assert "### Human Next Actions" in md
    assert "| group | action | paths | status | notes |" in md
    assert "| order | batch | action | paths | status | surfaces | notes |" in md
    assert "### Batch Warning Flags" in md
    assert "### Batch Review Gates" in md
    assert "### Batch Verification Targets" in md
    assert "### Batch Commit Message Hints" in md
    assert "### Batch Review Checklist" in md
    assert "### Batch Paths By Status" in md
    assert "### Batch Paths" in md
    assert "- batch_action_counts:" in md
    assert "- batch_warning_counts:" in md
    assert "- review_gate_counts:" in md
    assert "- verification_target_counts:" in md
    assert "Human review/staging reference only" in md
    assert "- `app/governance/change_handoff.py`" in md
    assert "confirm helpers validate metadata only" in md
    assert "no_external_action_authority" in md
    assert "push_allowed_for_agent=False" in md
    assert "human may stage reviewed batches separately; agent must not stage or push" in md
    assert "merge_allowed_for_agent=False" in md
    assert "verdict_authority=False" in md
    assert "pytest tests/test_change_handoff.py" in md
    assert "Skill/SOP governance helpers" in md
    assert "Add governance handoff helpers" in md
    assert "untracked_paths_present" in md
    assert "##### untracked" in md
    assert "{'untracked': 1}" in md
    assert "{'handoff_governance': 1}" in md
    assert "CHANGE SET" in md


def test_render_change_handoff_markdown_lists_each_batch_path():
    plan = change_handoff_plan(
        parse_git_status_short([
            " M app/benchmark/report_md.py",
            " M tests/test_benchmark.py",
            " M README.md",
            "D  docs/10_phase1/05_PHASE1_BACKLOG.md",
        ]),
        verification=[
            {
                "command": "pytest tests/test_benchmark.py",
                "result": "ok",
                "passed": True,
            }
        ],
        branch="main",
        unpushed_commits=0,
    )

    md = render_change_handoff_markdown(plan)

    assert "#### 1. api_smoke_report_projection" in md
    assert "### Batch Paths By Status" in md
    assert "##### modified" in md
    assert "##### deleted" in md
    assert "no_executor_or_verdict_drift" in md
    assert "tests/test_api_smoke_benchmark_projection.py" in md
    assert "Add API smoke report projection carry" in md
    assert "confirm API smoke changes remain report/projection/ledger carry/presentation only" in md
    assert "- `app/benchmark/report_md.py`" in md
    assert "- `tests/test_benchmark.py`" in md
    assert "#### 2. active_docs_and_handoff_context" in md
    assert "- `README.md`" in md
    assert "#### 3. historical_docs_prune" in md
    assert "- `docs/10_phase1/05_PHASE1_BACKLOG.md`" in md
    assert "does not stage, commit, push, or merge" in md
