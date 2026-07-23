"""Change-set handoff helpers for CI/PR preparation.

S5D2-S5D19 harden the ``ci-pr-handoff`` SOP as pure policy data. These
helpers do not read git state, stage, commit, push, merge, run tests, or grant
verdict authority. Callers pass observed status and command evidence in.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

CHANGE_HANDOFF_PLAN_VERSION = "change_handoff_plan.v1"

_ROOT_HANDOFF_FILES = {"AGENTS.md", "CLAUDE.md", "README.md"}
_FORBIDDEN_PATH_PARTS = {".env"}
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
_API_SMOKE_INTEGRATION_PATHS = {
    "app/api/submit_candidate.py",
    "app/benchmark/report_md.py",
    "app/ledger/__init__.py",
    "app/ledger/ingest.py",
    "app/ledger/models.py",
    "app/pipeline/submit_pipeline.py",
    "app/report/__init__.py",
    "app/report/generation_report.py",
    "tests/test_benchmark.py",
    "tests/test_ledger.py",
    "tests/test_submit_candidate.py",
    "tests/test_generation_report_api_smoke_manifest.py",
}
_ASSET_GATE_ROUTER_AUDIT_PATHS = {
    "docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md",
    "tests/test_test_level_router.py",
}
_JAVA_FRAMEWORK_NEUTRALITY_PATHS = {
    "app/report/java_test_framework.py",
    "docs/60_api_candidate/10_JAVA_TEST_FRAMEWORK_NEUTRALITY.md",
    "tests/test_generation_report.py",
    "tests/test_java_test_framework.py",
}
_PROJECT_PROGRESS_READINESS_PATHS = {
    "app/governance/__init__.py",
    "app/governance/landing_readiness.py",
    "app/governance/landing_readiness_report.py",
    "app/governance/project_progress.py",
    "docs/00_foundation/63_PROJECT_PROGRESS_SNAPSHOT.md",
    "tests/test_landing_readiness.py",
    "tests/test_landing_readiness_report.py",
    "tests/test_project_progress.py",
}
_LANDING_VALIDATION_READINESS_PATHS = {
    "app/benchmark/__init__.py",
    "app/benchmark/validation_line.py",
    "app/review/human_labels.py",
    "docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md",
    "docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md",
    "tests/test_human_labels.py",
    "tests/test_validation_line.py",
}
_HANDOFF_GOVERNANCE_PATHS = {
    "app/governance",
    "app/governance/change_handoff.py",
    "tests/test_change_handoff.py",
}
_SKILL_SOP_GOVERNANCE_PATHS = {
    "app/governance/skill_sop.py",
    "docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md",
    "tests/test_judge_skill_sop.py",
}
_RUNTIME_DOC_REFERENCE_CLEANUP_PATHS = {
    "app/__init__.py",
    "app/benchmark/business_tags.py",
    "app/main.py",
    "tests/e2e/test_phase1_e2e.py",
}


class ChangeHandoffValidationError(ValueError):
    """Raised when handoff input would violate CI/PR handoff guardrails."""


def parse_git_status_short(lines: Iterable[str]) -> list[dict[str, str]]:
    """Parse ``git status --short`` output into normalized change rows.

    The parser is intentionally small and pure. It handles ordinary modified,
    added, deleted, renamed, and untracked rows, preserving the raw two-character
    status for handoff evidence.
    """
    changes: list[dict[str, str]] = []
    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        if len(line) < 4:
            raise ChangeHandoffValidationError(
                f"git status line {index} is too short"
            )
        raw_status = line[:2]
        path_text = line[3:].strip()
        old_path = None
        if " -> " in path_text:
            old_path, path_text = path_text.split(" -> ", 1)
            old_path = old_path.strip() or None
            path_text = path_text.strip()
        changes.append({
            "path": _normalized_path(path_text),
            "status": _status_label(raw_status),
            "raw_status": raw_status,
            **({"old_path": _normalized_path(old_path)} if old_path else {}),
        })
    return changes


def change_handoff_plan(
    changes: Iterable[Mapping[str, Any]],
    verification: Iterable[Mapping[str, Any]] = (),
    *,
    branch: str | None = None,
    unpushed_commits: int | None = None,
    staged: bool = False,
    dirty: bool = True,
    push_performed: bool = False,
) -> dict[str, Any]:
    """Return a pure CI/PR handoff plan for observed changes.

    The output is a checklist for a human reviewer. It can recommend grouping
    and highlight gates, but it cannot authorize push/merge/adoption or claim
    engineering value.
    """
    normalized_changes = [_normalize_change(change) for change in changes]
    normalized_verification = [
        _normalize_verification(item) for item in verification
    ]
    blockers = _blocking_flags(
        normalized_verification,
        push_performed=push_performed,
    )
    warnings = _warning_flags(
        normalized_changes,
        staged=staged,
        dirty=dirty,
        unpushed_commits=unpushed_commits,
    )
    groups = _commit_groups(normalized_changes)
    batches = _commit_batches(groups)
    batch_action_counts = _batch_action_counts(batches)
    batch_warning_counts = _batch_warning_counts(batches)
    review_gate_counts = _review_gate_counts(batches)
    verification_target_counts = _verification_target_counts(batches)
    ready_for_human_handoff = not blockers and bool(normalized_verification)
    human_next_actions = _human_next_actions(
        batches,
        blockers,
        warnings,
        ready_for_human_handoff=ready_for_human_handoff,
    )

    return {
        "plan_version": CHANGE_HANDOFF_PLAN_VERSION,
        "advisory": True,
        "handoff_only": True,
        "branch": branch,
        "dirty_worktree": dirty,
        "staged_changes_present": staged,
        "unpushed_commits": unpushed_commits,
        "total_changes": len(normalized_changes),
        "by_status": _counter_dict(change["status"] for change in normalized_changes),
        "by_surface": _counter_dict(change["surface"] for change in normalized_changes),
        "changes": normalized_changes,
        "commit_groups": groups,
        "commit_batches": batches,
        "batch_action_counts": batch_action_counts,
        "batch_warning_counts": batch_warning_counts,
        "review_gate_counts": review_gate_counts,
        "verification_target_counts": verification_target_counts,
        "human_next_actions": human_next_actions,
        "verification": normalized_verification,
        "verification_passed": bool(normalized_verification)
        and all(item["passed"] is True for item in normalized_verification),
        "blocking_flags": blockers,
        "warning_flags": warnings,
        "ready_for_human_handoff": ready_for_human_handoff,
        "push_allowed_for_agent": False,
        "merge_allowed_for_agent": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "red_lines": [
            "human_push_only",
            "no_auto_merge",
            "no_claim_without_command_evidence",
            "do_not_hide_unrelated_dirty_changes",
            "no_verdict_or_trusted_status_authority",
        ],
        "note": (
            "Pure handoff checklist. It does not stage, commit, push, merge, run "
            "tests, or change candidate verdicts."
        ),
    }


def render_change_handoff_markdown(plan: Mapping[str, Any]) -> str:
    """Render a compact handoff summary for a human reviewer."""
    lines = [
        "## CI/PR handoff - CHANGE SET",
        "",
        f"- plan_version: {plan.get('plan_version')}",
        f"- branch: {_cell(plan.get('branch') or 'unknown')}",
        f"- total_changes: {plan.get('total_changes')}  "
        f"dirty_worktree: {plan.get('dirty_worktree')}  "
        f"staged_changes_present: {plan.get('staged_changes_present')}  "
        f"unpushed_commits: {plan.get('unpushed_commits')}",
        f"- by_status: {plan.get('by_status')}",
        f"- by_surface: {plan.get('by_surface')}",
        f"- verification_passed: {plan.get('verification_passed')}  "
        f"ready_for_human_handoff: {plan.get('ready_for_human_handoff')}",
        f"- blocking_flags: {plan.get('blocking_flags')}",
        f"- warning_flags: {plan.get('warning_flags')}",
        f"- batch_action_counts: {plan.get('batch_action_counts')}",
        f"- batch_warning_counts: {plan.get('batch_warning_counts')}",
        f"- review_gate_counts: {plan.get('review_gate_counts')}",
        f"- verification_target_counts: {plan.get('verification_target_counts')}",
        "- authority: push_allowed_for_agent="
        f"{plan.get('push_allowed_for_agent')}  "
        f"merge_allowed_for_agent={plan.get('merge_allowed_for_agent')}  "
        f"verdict_authority={plan.get('verdict_authority')}  "
        f"trusted_authority={plan.get('trusted_authority')}",
        "  (human push/merge only; command evidence required)",
        "",
        "| group | action | paths | status | notes |",
        "|---|---|---:|---|---|",
    ]
    if plan.get("human_next_actions"):
        lines += ["", "### Human Next Actions", ""]
        for action in plan["human_next_actions"]:
            lines.append(f"- {_cell(action)}")
        lines.append("")
    for group in plan.get("commit_groups", []):
        lines.append(
            f"| {_cell(group.get('name'))} "
            f"| {_cell(group.get('recommended_action'))} "
            f"| {len(group.get('paths') or [])} "
            f"| {_cell(group.get('status_counts') or {})} "
            f"| {_cell(group.get('notes') or [])} |"
        )
    if plan.get("commit_batches"):
        lines += ["", "### Suggested Commit Batches", ""]
        lines += [
            "| order | batch | action | paths | status | surfaces | notes |",
            "|---:|---|---|---:|---|---|---|",
        ]
        for batch in plan["commit_batches"]:
            lines.append(
                f"| {batch.get('order')} "
                f"| {_cell(batch.get('name'))} "
                f"| {_cell(batch.get('recommended_action'))} "
                f"| {len(batch.get('paths') or [])} "
                f"| {_cell(batch.get('status_counts') or {})} "
                f"| {_cell(batch.get('surface_counts') or {})} "
                f"| {_cell(batch.get('notes') or [])} |"
            )
        lines += ["", "### Batch Warning Flags", ""]
        lines += ["| order | batch | warnings |", "|---:|---|---|"]
        for batch in plan["commit_batches"]:
            lines.append(
                f"| {batch.get('order')} "
                f"| {_cell(batch.get('name'))} "
                f"| {_cell(batch.get('warning_flags') or [])} |"
            )
        lines += ["", "### Batch Review Gates", ""]
        lines += ["| order | batch | gates |", "|---:|---|---|"]
        for batch in plan["commit_batches"]:
            lines.append(
                f"| {batch.get('order')} "
                f"| {_cell(batch.get('name'))} "
                f"| {_cell(batch.get('review_gates') or [])} |"
            )
        lines += ["", "### Batch Verification Targets", ""]
        for batch in plan["commit_batches"]:
            lines += [
                f"#### {batch.get('order')}. {_cell(batch.get('name'))}",
                "",
            ]
            for target in batch.get("verification_targets") or []:
                lines.append(
                    f"- `{_cell(target.get('command'))}` - "
                    f"{_cell(target.get('purpose'))}"
                )
            lines.append("")
        lines += ["", "### Batch Commit Message Hints", ""]
        lines += ["| order | batch | commit message hint |", "|---:|---|---|"]
        for batch in plan["commit_batches"]:
            lines.append(
                f"| {batch.get('order')} "
                f"| {_cell(batch.get('name'))} "
                f"| {_cell(batch.get('commit_message_hint'))} |"
            )
        lines += ["", "### Batch Review Checklist", ""]
        for batch in plan["commit_batches"]:
            lines += [
                f"#### {batch.get('order')}. {_cell(batch.get('name'))}",
                "",
            ]
            for item in batch.get("review_checklist") or []:
                lines.append(f"- {_cell(item)}")
            lines.append("")
        lines += [
            "",
            "### Batch Paths By Status",
            "",
            "Human review/staging reference only; grouped by observed git status.",
            "",
        ]
        for batch in plan["commit_batches"]:
            lines += [
                f"#### {batch.get('order')}. {_cell(batch.get('name'))}",
                "",
            ]
            for status, paths in (batch.get("paths_by_status") or {}).items():
                lines += [f"##### {_cell(status)}", ""]
                for path in paths:
                    lines.append(f"- `{_cell(path)}`")
                lines.append("")
        lines += [
            "",
            "### Batch Paths",
            "",
            "Human review/staging reference only; this helper does not stage, commit, push, or merge.",
            "",
        ]
        for batch in plan["commit_batches"]:
            lines += [
                f"#### {batch.get('order')}. {_cell(batch.get('name'))}",
                "",
            ]
            for path in batch.get("paths") or []:
                lines.append(f"- `{_cell(path)}`")
            lines.append("")
    if plan.get("verification"):
        lines += ["", "### Verification", ""]
        for item in plan["verification"]:
            lines.append(
                f"- {_cell(item.get('command'))}: {_cell(item.get('result'))} "
                f"(passed={item.get('passed')})"
            )
    lines.append("")
    return "\n".join(lines)


def _normalize_change(change: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(change, Mapping):
        raise ChangeHandoffValidationError("change must be a mapping")
    path = _normalized_path(change.get("path"))
    status = str(change.get("status", "")).strip().lower()
    if status in {"??", "untracked"}:
        status = "untracked"
    elif status in {"m", "modified", "change", "changed"}:
        status = "modified"
    elif status in {"a", "added", "new"}:
        status = "added"
    elif status in {"d", "deleted", "removed"}:
        status = "deleted"
    elif status in {"r", "renamed"}:
        status = "renamed"
    elif status not in {"copied", "mixed"}:
        raise ChangeHandoffValidationError(f"unsupported change status: {status!r}")
    return {
        "path": path,
        "status": status,
        "surface": _surface_for_path(path, status),
    }


def _normalize_verification(item: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise ChangeHandoffValidationError("verification item must be a mapping")
    command = _required_text(item.get("command"), "verification.command")
    result = _required_text(item.get("result"), "verification.result")
    passed = item.get("passed")
    if not isinstance(passed, bool):
        raise ChangeHandoffValidationError("verification.passed must be boolean")
    return {
        "command": command,
        "result": result,
        "passed": passed,
    }


def _normalized_path(value: Any) -> str:
    path = _required_text(value, "path").replace("\\", "/")
    if path.startswith("/") or ":" in path.split("/", 1)[0]:
        raise ChangeHandoffValidationError("path must be repo-relative")
    parts = [part for part in path.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise ChangeHandoffValidationError("path must stay within the repo")
    lowered_parts = [part.lower() for part in parts]
    if any(
        part in _FORBIDDEN_PATH_PARTS or part.startswith(".env.")
        for part in lowered_parts
    ):
        raise ChangeHandoffValidationError("handoff must not include .env paths")
    if parts[-1].lower().endswith(_SECRET_SUFFIXES):
        raise ChangeHandoffValidationError("handoff must not include secret key files")
    return "/".join(parts)


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChangeHandoffValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _status_label(raw_status: str) -> str:
    if raw_status == "??":
        return "untracked"
    if "R" in raw_status:
        return "renamed"
    if "D" in raw_status:
        return "deleted"
    if "A" in raw_status:
        return "added"
    if "M" in raw_status:
        return "modified"
    if "C" in raw_status:
        return "copied"
    return "mixed"


def _surface_for_path(path: str, status: str) -> str:
    if status == "deleted" and path.startswith("docs/"):
        return "docs_prune"
    if _is_java_framework_neutrality_path(path):
        return "java_framework_neutrality"
    if _is_api_smoke_path(path):
        return "api_smoke_report_projection"
    if _is_asset_gate_router_path(path):
        return "asset_gate_router_audit"
    if _is_project_progress_readiness_path(path):
        return "project_progress_readiness"
    if _is_landing_validation_readiness_path(path):
        return "landing_validation_readiness"
    if _is_skill_sop_governance_path(path):
        return "skill_sop_governance"
    if _is_handoff_governance_path(path):
        return "handoff_governance"
    if _is_runtime_doc_reference_cleanup_path(path):
        return "runtime_doc_reference_cleanup"
    if _is_golden_manifest_path(path):
        return "golden_manifest_governance"
    if _is_external_asset_path(path):
        return "external_asset_governance"
    if path in _ROOT_HANDOFF_FILES:
        return "root_handoff_docs"
    if path.startswith("docs/"):
        return "docs_boundary"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("app/"):
        return "runtime_code"
    if path.startswith("benchmarks/"):
        return "benchmark_manifest"
    if path.startswith("scripts/"):
        return "scripts"
    return "other"


def _is_api_smoke_path(path: str) -> bool:
    return (
        "api_smoke" in path
        or "api_evidence" in path
        or path in _API_SMOKE_INTEGRATION_PATHS
        or path.startswith("docs/60_api_candidate/")
        or path in {
            "docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md",
            "docs/50_benchmark/60_API_SMOKE_LEDGER_PROJECTION_DESIGN.md",
        }
    )


def _is_golden_manifest_path(path: str) -> bool:
    return (
        "manifest_governance" in path
        or "golden_manifest" in path
        or path == "docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md"
    )


def _is_asset_gate_router_path(path: str) -> bool:
    return path in _ASSET_GATE_ROUTER_AUDIT_PATHS


def _is_java_framework_neutrality_path(path: str) -> bool:
    return path in _JAVA_FRAMEWORK_NEUTRALITY_PATHS


def _is_project_progress_readiness_path(path: str) -> bool:
    return path in _PROJECT_PROGRESS_READINESS_PATHS


def _is_landing_validation_readiness_path(path: str) -> bool:
    return path in _LANDING_VALIDATION_READINESS_PATHS


def _is_handoff_governance_path(path: str) -> bool:
    return path in _HANDOFF_GOVERNANCE_PATHS


def _is_skill_sop_governance_path(path: str) -> bool:
    return path in _SKILL_SOP_GOVERNANCE_PATHS


def _is_runtime_doc_reference_cleanup_path(path: str) -> bool:
    return path in _RUNTIME_DOC_REFERENCE_CLEANUP_PATHS


def _is_external_asset_path(path: str) -> bool:
    return (
        path.startswith("app/governance/")
        or "external_asset" in path
        or "external_repo" in path
        or path.startswith("docs/knowledge/EXTERNAL_")
        or path == "docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md"
    )


def _commit_groups(changes: list[Mapping[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, str]]] = {}
    for change in changes:
        surface = change["surface"]
        grouped.setdefault(surface, []).append(change)

    return [
        {
            "name": surface,
            "recommended_action": _recommended_action(surface),
            "paths": sorted(change["path"] for change in surface_changes),
            "status_counts": _counter_dict(
                change["status"] for change in surface_changes
            ),
            "paths_by_status": _paths_by_status(surface_changes),
            "notes": _surface_notes(surface),
        }
        for surface, surface_changes in sorted(grouped.items())
    ]


def _commit_batches(groups: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Map surface groups to suggested human-review commit batches."""
    grouped = {group["name"]: group for group in groups}
    specs = [
        {
            "name": "api_smoke_report_projection",
            "surfaces": ["api_smoke_report_projection"],
            "recommended_action": "keep",
            "notes": [
                "report/projection/ledger carry/presentation only",
                "includes red-line descriptive counts only in named API smoke views",
                "no executor, digest, signature, existing analytics, or verdict change",
            ],
            "commit_message_hint": "Add API smoke report projection carry",
            "review_checklist": [
                "confirm API smoke changes remain report/projection/ledger carry/presentation only",
                "confirm no executor, service orchestration, digest severity, signature, existing analytics, or verdict/trust change",
                "rerun API smoke benchmark/ledger/report target tests before staging",
            ],
            "review_gates": [
                "human_review_required",
                "verification_required",
                "no_executor_or_verdict_drift",
            ],
            "verification_targets": [
                {
                    "command": (
                        "pytest tests/test_api_smoke_projection_boundary.py "
                        "tests/test_api_smoke_benchmark_projection.py "
                        "tests/test_benchmark.py "
                        "tests/test_api_smoke_ledger_projection.py"
                    ),
                    "purpose": (
                        "API smoke benchmark and ledger projection presentation"
                    ),
                },
                {
                    "command": (
                        "pytest tests/test_submit_candidate.py "
                        "tests/test_generation_report_api_smoke_manifest.py "
                        "tests/test_ledger.py"
                    ),
                    "purpose": "submit/report/ledger carry-through safety",
                },
            ],
        },
        {
            "name": "java_framework_neutrality",
            "surfaces": ["java_framework_neutrality"],
            "recommended_action": "keep",
            "notes": [
                "report-only Java framework facts",
                "optional submit declarations carry into the same report-only facts",
                "JUnit stays thin; TestNG is visible without runner or verdict authority",
            ],
            "commit_message_hint": "Add Java test framework neutrality facts",
            "review_checklist": [
                "confirm framework facts are advisory and report-only",
                "confirm submit_candidate accepts only normalized report-only declarations",
                "confirm no dependency install, POM mutation, runner change, or generator tuning",
                "rerun Java framework and generation report target tests before staging",
            ],
            "review_gates": [
                "human_review_required",
                "verification_required",
                "no_runner_or_verdict_drift",
            ],
            "verification_targets": [
                {
                    "command": (
                        "pytest tests/test_java_test_framework.py "
                        "tests/test_submit_candidate.py "
                        "tests/test_generation_report.py "
                        "tests/test_generation_report_api_evidence.py"
                    ),
                    "purpose": "Java framework report facts and report assembly safety",
                },
            ],
        },
        {
            "name": "landing_readiness_snapshots",
            "surfaces": [
                "project_progress_readiness",
                "landing_validation_readiness",
            ],
            "recommended_action": "keep",
            "notes": [
                "advisory project progress and landing-metric readiness only",
                "human/golden labels can make metrics computable but not headline-approved",
                "no executor, persistence, git, verdict, or trust authority",
            ],
            "commit_message_hint": "Add landing readiness snapshots",
            "review_checklist": [
                "confirm progress percent remains advisory planning metadata",
                "confirm human/golden readiness does not create headline metric authority",
                "confirm no executor, persistence, git action, digest severity, verdict, or trust change",
                "rerun progress and validation readiness tests before staging",
            ],
            "review_gates": [
                "human_review_required",
                "verification_required",
                "no_headline_or_verdict_authority",
            ],
            "verification_targets": [
                {
                    "command": (
                        "pytest tests/test_landing_readiness.py "
                        "tests/test_landing_readiness_report.py "
                        "tests/test_project_progress.py "
                        "tests/test_validation_line.py "
                        "tests/test_human_labels.py"
                    ),
                    "purpose": (
                        "project progress and human/golden metric readiness "
                        "boundaries"
                    ),
                },
            ],
        },
        {
            "name": "governance_helpers",
            "surfaces": [
                "external_asset_governance",
                "golden_manifest_governance",
                "handoff_governance",
                "skill_sop_governance",
            ],
            "recommended_action": "keep",
            "notes": [
                "metadata, Skill/SOP readiness, and handoff governance only",
                "Golden Set defect denominator readiness remains metadata-only",
                "no download, install, push, merge, or verdict authority",
            ],
            "commit_message_hint": "Add governance handoff helpers",
            "review_checklist": [
                "confirm helpers validate metadata only and perform no download/install/git action",
                "confirm external assets remain owner-gated with no runtime authority",
                "confirm Golden Set denominator readiness grants no dataset, verifier, or headline authority",
                "confirm Skill/SOP blueprints reuse existing judge entrypoints only",
                "rerun governance helper target tests before staging",
            ],
            "review_gates": [
                "human_review_required",
                "verification_required",
                "no_external_action_authority",
            ],
            "verification_targets": [
                {
                    "command": (
                        "pytest tests/test_change_handoff.py "
                        "tests/test_external_asset_phase_policy.py "
                        "tests/test_external_repo_readme_audit.py "
                        "tests/test_judge_skill_sop.py"
                    ),
                    "purpose": "handoff, external-asset, and Skill/SOP governance helpers",
                },
                {
                    "command": (
                        "pytest tests/test_golden_manifest_governance.py "
                        "tests/test_golden_manifest_governance_report.py"
                    ),
                    "purpose": "Golden Set manifest governance presentation",
                },
            ],
        },
        {
            "name": "active_docs_and_handoff_context",
            "surfaces": [
                "asset_gate_router_audit",
                "root_handoff_docs",
                "runtime_doc_reference_cleanup",
                "docs_boundary",
                "benchmark_manifest",
            ],
            "recommended_action": "keep",
            "notes": [
                "current boundary/readme/manifest context",
                "review for stale cross references before commit",
            ],
            "commit_message_hint": "Refresh active docs and handoff context",
            "review_checklist": [
                "confirm active docs point to WORK_LOG, docs README, and current boundary docs",
                "confirm runtime doc-reference cleanup is docstring/comment only",
                "confirm benchmark manifests are metadata-only and headline semantics do not drift",
            ],
            "review_gates": [
                "human_review_required",
                "cross_reference_review_required",
                "no_headline_metric_drift",
            ],
            "verification_targets": [
                {
                    "command": (
                        "pytest tests/test_test_level_router.py "
                        "tests/test_change_handoff.py"
                    ),
                    "purpose": "router boundary and handoff classification safety",
                },
                {
                    "command": "pytest tests/e2e/test_phase1_e2e.py",
                    "purpose": (
                        "runtime doc-reference cleanup guard "
                        "(skips unless TESTAGENT_E2E=1)"
                    ),
                },
            ],
        },
        {
            "name": "historical_docs_prune",
            "surfaces": ["docs_prune"],
            "recommended_action": "keep_with_owner_awareness",
            "notes": [
                "large active-tree deletion",
                "commit separately so review can inspect pruning intent",
            ],
            "commit_message_hint": "Prune historical docs from active tree",
            "review_checklist": [
                "confirm owner is aware pruned docs are removed from the active tree",
                "confirm active docs explain recovery from git history for archaeology",
                "stage pruning separately from runtime/report/governance changes",
            ],
            "review_gates": [
                "owner_awareness_required",
                "stage_separately",
                "recover_from_git_history_for_archaeology",
            ],
            "verification_targets": [
                {
                    "command": "pytest tests/test_change_handoff.py",
                    "purpose": "prune batch remains owner-awareness handoff only",
                },
            ],
        },
        {
            "name": "residual_runtime_and_tests",
            "surfaces": ["runtime_code", "tests", "scripts", "other"],
            "recommended_action": "review_before_keep",
            "notes": [
                "mixed leftovers",
                "inspect paths before staging into a final commit",
            ],
            "commit_message_hint": "Review residual runtime and test changes",
            "review_checklist": [
                "inspect every residual path before keeping it",
                "rerun focused tests for residual runtime/test paths",
                "do not stage with keep batches until intent is explained",
            ],
            "review_gates": [
                "residual_review_required",
                "focused_tests_required",
                "do_not_stage_with_keep_batches",
            ],
            "verification_targets": [
                {
                    "command": "pytest <focused tests for residual paths>",
                    "purpose": "must be chosen after inspecting residual paths",
                },
            ],
        },
    ]
    batches: list[dict[str, Any]] = []
    for spec in specs:
        paths: list[str] = []
        included_surfaces: list[str] = []
        surface_counts: dict[str, int] = {}
        status_counter: Counter[str] = Counter()
        paths_by_status: dict[str, list[str]] = {}
        for surface in spec["surfaces"]:
            group = grouped.get(surface)
            if not group:
                continue
            group_paths = group.get("paths") or []
            paths.extend(group_paths)
            surface_counts[surface] = len(group_paths)
            status_counter.update(group.get("status_counts") or {})
            for status, status_paths in (group.get("paths_by_status") or {}).items():
                paths_by_status.setdefault(str(status), []).extend(status_paths)
            included_surfaces.append(surface)
        if not paths:
            continue
        order = len(batches) + 1
        batches.append({
            "order": order,
            "name": spec["name"],
            "surfaces": included_surfaces,
            "surface_counts": surface_counts,
            "recommended_action": spec["recommended_action"],
            "paths": sorted(paths),
            "status_counts": dict(status_counter.most_common()),
            "paths_by_status": {
                status: sorted(paths_by_status.get(status, []))
                for status, _ in status_counter.most_common()
            },
            "commit_message_hint": spec["commit_message_hint"],
            "warning_flags": _batch_warning_flags(
                spec["recommended_action"],
                surface_counts,
                status_counter,
            ),
            "notes": list(spec["notes"]),
            "review_checklist": list(spec["review_checklist"]),
            "review_gates": list(spec["review_gates"]),
            "verification_targets": [
                dict(target) for target in spec["verification_targets"]
            ],
        })
    return batches


def _review_gate_counts(batches: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    return _counter_dict(
        str(gate)
        for batch in batches
        for gate in batch.get("review_gates", [])
        if gate
    )


def _batch_action_counts(batches: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    return _counter_dict(
        str(batch.get("recommended_action"))
        for batch in batches
        if batch.get("recommended_action")
    )


def _batch_warning_counts(batches: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    return _counter_dict(
        str(flag)
        for batch in batches
        for flag in batch.get("warning_flags", [])
        if flag
    )


def _batch_warning_flags(
    recommended_action: str,
    surface_counts: Mapping[str, int],
    status_counts: Mapping[str, int],
) -> list[str]:
    flags: list[str] = []
    if status_counts.get("untracked", 0) > 0:
        flags.append("untracked_paths_present")
    if surface_counts.get("docs_prune", 0) > 0:
        flags.append("docs_prune_requires_owner_awareness")
    if recommended_action == "review_before_keep":
        flags.append("review_before_keep")
    return flags


def _paths_by_status(changes: Iterable[Mapping[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for change in changes:
        grouped.setdefault(change["status"], []).append(change["path"])
    return {
        status: sorted(paths)
        for status, paths in sorted(grouped.items())
    }


def _verification_target_counts(
    batches: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    return {
        str(batch["name"]): len(batch.get("verification_targets") or [])
        for batch in batches
        if batch.get("name")
    }


def _human_next_actions(
    batches: Iterable[Mapping[str, Any]],
    blockers: Iterable[str],
    warnings: Iterable[str],
    *,
    ready_for_human_handoff: bool,
) -> list[str]:
    batch_list = list(batches)
    actions: list[str] = []
    blocker_list = list(blockers)
    warning_set = set(warnings)
    if blocker_list:
        actions.append("resolve blocking flags before staging")
    if "untracked_files_present" in warning_set:
        actions.append("review untracked paths in each keep batch before staging")
    if any(batch.get("recommended_action") == "keep_with_owner_awareness" for batch in batch_list):
        actions.append("confirm owner awareness before staging docs-prune batch")
    if any(batch.get("verification_targets") for batch in batch_list):
        actions.append("rerun suggested verification targets for each batch before commit")
    if ready_for_human_handoff:
        actions.append("human may stage reviewed batches separately; agent must not stage or push")
    return actions


def _recommended_action(surface: str) -> str:
    if surface == "docs_prune":
        return "keep_with_owner_awareness"
    if surface in {
        "api_smoke_report_projection",
        "external_asset_governance",
        "asset_gate_router_audit",
        "java_framework_neutrality",
        "project_progress_readiness",
        "landing_validation_readiness",
        "golden_manifest_governance",
        "handoff_governance",
        "skill_sop_governance",
        "runtime_doc_reference_cleanup",
        "root_handoff_docs",
        "docs_boundary",
        "tests",
    }:
        return "keep"
    return "review_before_keep"


def _surface_notes(surface: str) -> list[str]:
    notes = {
        "api_smoke_report_projection": [
            "report/projection/ledger carry/presentation only",
            "API smoke red-line counts are descriptive only",
            "no executor, existing analytics, or verdict authority",
        ],
        "external_asset_governance": [
            "metadata/audit policy only",
            "no download, install, execution, or vendoring",
        ],
        "asset_gate_router_audit": [
            "report-only Test-Level Router closeout",
            "no executor, digest flag, carry, aggregate, or verdict authority",
        ],
        "java_framework_neutrality": [
            "report-only Java framework facts",
            "TestNG visibility without dependency install, runner change, or verdict authority",
        ],
        "golden_manifest_governance": [
            "manifest_seed metadata only",
            "defect denominator readiness stays future-only",
            "no dataset slice, verifier execution, or headline metric",
        ],
        "project_progress_readiness": [
            "advisory completion snapshot only",
            "no runtime, git, executor, verdict, or trust authority",
        ],
        "landing_validation_readiness": [
            "human/golden metric readiness only",
            "no persistence, headline metric, verdict, or trust authority",
        ],
        "handoff_governance": [
            "change-set handoff policy only",
            "no git read, stage, commit, push, merge, or verdict authority",
        ],
        "skill_sop_governance": [
            "Skill/SOP readiness policy only",
            "no Skill install, agent runtime, model call, executor, or verdict authority",
        ],
        "runtime_doc_reference_cleanup": [
            "docstring/comment references moved from pruned docs to active docs",
            "no runtime behavior change expected; review diff before staging",
        ],
        "docs_prune": [
            "large active-tree deletion",
            "recover historical docs from git history when needed",
        ],
        "root_handoff_docs": ["agent and README handoff context"],
        "tests": ["verification coverage"],
    }
    return notes.get(surface, [])


def _blocking_flags(
    verification: list[Mapping[str, Any]],
    *,
    push_performed: bool,
) -> list[str]:
    flags: list[str] = []
    if push_performed:
        flags.append("push_already_performed_by_agent")
    if not verification:
        flags.append("verification_missing")
    elif any(item["passed"] is not True for item in verification):
        flags.append("verification_failed")
    return flags


def _warning_flags(
    changes: list[Mapping[str, str]],
    *,
    staged: bool,
    dirty: bool,
    unpushed_commits: int | None,
) -> list[str]:
    flags: list[str] = []
    if any(change["surface"] == "docs_prune" for change in changes):
        flags.append("docs_prune_requires_owner_awareness")
    if any(
        change["surface"] in {"runtime_code", "tests", "scripts", "other"}
        for change in changes
    ):
        flags.append("residual_runtime_or_tests_need_review")
    if any(change["status"] == "untracked" for change in changes):
        flags.append("untracked_files_present")
    if dirty and not staged:
        flags.append("dirty_worktree_not_staged")
    if unpushed_commits is None:
        flags.append("unpushed_count_unknown")
    elif unpushed_commits > 0:
        flags.append("unpushed_commits_present")
    return flags


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values).most_common())


def _cell(value: Any) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    else:
        text = "" if value is None else str(value)
    return text.replace("|", "/").replace("\n", " ").strip()
