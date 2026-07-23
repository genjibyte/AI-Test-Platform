"""Project progress snapshot for judge-first completion planning.

The helper is pure policy data. It does not inspect git, run tests, call
models, execute tools, change verdicts, or grant trust. Its purpose is to make
the otherwise fuzzy "percent complete" discussion auditable.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

PROJECT_PROGRESS_SNAPSHOT_VERSION = "project_progress_snapshot.v1"

_CURRENT_COMPONENTS: tuple[dict[str, Any], ...] = (
    {
        "id": "judge_kernel_execution_evidence",
        "pillar": "Candidate",
        "weight": 22,
        "completion_percent": 82,
        "status": "late_core_hardened",
        "evidence": [
            "Maven/Surefire/JaCoCo execution kernel is live",
            "preflight and quality gate are live",
            "full offline pytest evidence exists",
        ],
        "remaining": [
            "runner/parser robustness on more real repos",
            "owner-gated non-unit candidate executor design",
        ],
    },
    {
        "id": "producer_agnostic_candidate_entry",
        "pillar": "Candidate",
        "weight": 13,
        "completion_percent": 80,
        "status": "live_with_report_only_extensions",
        "evidence": [
            "submit_candidate is live",
            "producer_id and run_kind=external are carried as provenance",
            "candidate_kind, api_evidence, api_smoke_manifest, and java_test_framework carry are report-only",
        ],
        "remaining": [
            "future candidate-kind naming cleanup",
            "external producer batch ingestion remains future design",
        ],
    },
    {
        "id": "quality_review_signal_layer",
        "pillar": "Asset Gate",
        "weight": 16,
        "completion_percent": 76,
        "status": "advisory_signals_live",
        "evidence": [
            "quality gate, oracle strength, invariant review, mock smell, Asset Gate, Test-Level Router, and review digest are live",
            "Java framework facts are report-only",
        ],
        "remaining": [
            "human calibration for signal usefulness",
            "no digest severity expansion without owner-approved design",
        ],
    },
    {
        "id": "badcase_benchmark_memory",
        "pillar": "Badcase",
        "weight": 14,
        "completion_percent": 68,
        "status": "ledger_and_named_projections_live",
        "evidence": [
            "badcase ledger and retrieval are live",
            "run_kind-aware benchmark aggregates are live",
            "API-smoke benchmark and ledger projections are named and separated",
        ],
        "remaining": [
            "more real badcase population",
            "human RCA labels before stronger claims",
        ],
    },
    {
        "id": "api_interface_candidate_evaluation",
        "pillar": "Candidate",
        "weight": 17,
        "completion_percent": 58,
        "status": "report_submit_projection_only",
        "evidence": [
            "junit_api_candidate report-only evidence path is live",
            "api_smoke_manifest, denominator policy, benchmark projection, and ledger projection are live",
        ],
        "remaining": [
            "no API executor yet",
            "no service orchestration or external SUT path yet",
            "API/interface implementation design is lower priority until the joint human+Golden evidence slice exists",
        ],
    },
    {
        "id": "real_world_validation_and_golden_set",
        "pillar": "Provenance",
        "weight": 10,
        "completion_percent": 50,
        "status": "metadata_contracts_label_and_denominator_readiness_live",
        "evidence": [
            "real-world validation line contract is live",
            "human/golden label metric readiness summary is live",
            "Golden Set defect-denominator readiness summary is live",
            "Golden Set manifest_seed governance is metadata-only live",
        ],
        "remaining": [
            "usable-test rate, defect discovery, diagnosis time, and misjudgment rate need human/golden labels",
            "human labels and Golden Set denominator metadata must advance as one closure slice",
            "dataset slices remain owner-gated",
        ],
    },
    {
        "id": "governance_handoff_reuse_skill_readiness",
        "pillar": "Provenance",
        "weight": 8,
        "completion_percent": 76,
        "status": "metadata_governance_live_frozen_for_closure",
        "evidence": [
            "external asset phase policy and reuse-check governance are live",
            "change-set handoff helper is live",
            "Skill/SOP blueprint readiness is metadata-only live",
            "landing readiness rollup, blocker-family summary/validator/Markdown, Markdown presentation, review checklist, typed boundary validator, and derived-consistency validator are metadata-only live",
            "S6 landing-readiness governance is frozen unless a real high-risk boundary bug appears",
        ],
        "remaining": [
            "human batch review/staging still required",
            "Skill installation remains future owner-gated",
            "do not add more S6 landing-readiness hardening as normal progress work",
        ],
    },
)

_AUTHORITY_FLAGS = {
    "runtime_authority": False,
    "executor_authority": False,
    "dependency_install_allowed": False,
    "pom_mutation_allowed": False,
    "external_execution_allowed": False,
    "model_call_allowed": False,
    "git_stage_commit_push_authority": False,
    "digest_authority": False,
    "verdict_authority": False,
    "trusted_authority": False,
}


class ProjectProgressValidationError(ValueError):
    """Raised when progress override data is invalid."""


def project_progress_snapshot(
    component_overrides: Mapping[str, int | float] | None = None,
) -> dict[str, Any]:
    """Return the current weighted project completion snapshot.

    ``component_overrides`` is only for scenario planning in tests/design
    reviews. Unknown component ids or values outside 0..100 are rejected.
    """
    components = deepcopy(list(_CURRENT_COMPONENTS))
    overrides = _normalize_overrides(component_overrides)
    for component in components:
        if component["id"] in overrides:
            component["completion_percent"] = overrides[component["id"]]

    total_weight = sum(component["weight"] for component in components)
    weighted = sum(
        component["weight"] * component["completion_percent"]
        for component in components
    )
    overall = round(weighted / total_weight)

    return {
        "schema_version": PROJECT_PROGRESS_SNAPSHOT_VERSION,
        "advisory": True,
        "report_only": True,
        "stage": _stage_for_percent(overall),
        "overall_completion_percent": overall,
        "completion_band": _completion_band(overall),
        "confidence": "medium",
        "components": components,
        "not_80_yet_because": [
            "API/interface candidate evaluation is still report/submit/projection only",
            "joint human-label plus Golden Set evidence is not populated enough for landing claims",
            "human review/staging/commit remains required for the large existing change set",
        ],
        "next_best_steps": [
            "freeze S6 landing-readiness governance unless a real high-risk boundary bug appears",
            "build one small joint human-label plus Golden Set evidence slice before stronger outcome metrics",
            "defer owner-gated API/interface implementation design until the joint evidence slice exposes a concrete need",
        ],
        "red_lines": [
            "do not treat legacy JUnit generation as product direction",
            "do not continue S6R/S6S-style governance hardening without a concrete high-risk bug",
            "do not add executor, dependency, POM mutation, or external SUT work without owner gate",
            "do not change conclusion=NEED_HUMAN_REVIEW or trusted=False",
            "do not stage, commit, or push from the agent handoff path",
        ],
        **_AUTHORITY_FLAGS,
    }


def _normalize_overrides(
    overrides: Mapping[str, int | float] | None,
) -> dict[str, int]:
    if overrides is None:
        return {}
    if not isinstance(overrides, Mapping):
        raise ProjectProgressValidationError("component_overrides must be a mapping")
    known = {component["id"] for component in _CURRENT_COMPONENTS}
    normalized: dict[str, int] = {}
    for key, value in overrides.items():
        if key not in known:
            raise ProjectProgressValidationError(f"unknown progress component {key!r}")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ProjectProgressValidationError(
                f"completion override for {key!r} must be numeric"
            )
        if value < 0 or value > 100:
            raise ProjectProgressValidationError(
                f"completion override for {key!r} must be between 0 and 100"
            )
        normalized[key] = round(value)
    return normalized


def _stage_for_percent(percent: int) -> str:
    if percent < 50:
        return "foundation_building"
    if percent < 65:
        return "core_integration"
    if percent < 80:
        return "late_core_harness_hardening_pre_80"
    if percent < 90:
        return "landing_validation"
    return "release_candidate"


def _completion_band(percent: int) -> str:
    if percent < 65:
        return "below_65"
    if percent < 75:
        return "around_70"
    if percent < 80:
        return "approaching_80"
    if percent < 90:
        return "past_80_not_release_ready"
    return "near_release"
