"""Judge Skill/SOP readiness tests."""
from __future__ import annotations

import pytest

from app.governance import (
    JUDGE_SKILL_BLUEPRINT_SCHEMA_VERSION,
    JUDGE_SKILL_READINESS_PLAN_VERSION,
    JudgeSkillBlueprintValidationError,
    candidate_eval_skill_readiness_plan,
    judge_skill_readiness_plan,
    validate_judge_skill_blueprint,
)


def _blueprint(**overrides):
    blueprint = {
        "schema_version": JUDGE_SKILL_BLUEPRINT_SCHEMA_VERSION,
        "name": "unit-test-candidate-eval",
        "skill_form": "codex_skill_blueprint",
        "trigger": "A Java/Maven/JUnit test candidate needs judgment.",
        "inputs": [
            "target_class",
            "test_source",
            "producer_id",
        ],
        "steps": [
            "submit through the existing candidate path",
            "collect compile, Surefire, coverage, quality gate, and digest evidence",
            "summarize observed facts for human review",
        ],
        "evidence": [
            "judge command or pipeline result",
            "compile/build status",
            "review_summary.digest",
        ],
        "red_lines": [
            "conclusion must remain NEED_HUMAN_REVIEW",
            "trusted=False must remain fixed",
            "no auto-accept or auto-merge",
            "command evidence beats generated claims",
        ],
        "output": [
            "candidate evidence summary",
            "review risks",
            "human-review checklist",
        ],
        "fallback": "If command evidence is missing, mark the candidate unverified.",
        "verification": [
            "run existing offline judge or pytest evidence checks",
            "confirm conclusion and trusted fields are unchanged",
        ],
        "pillars": ["Candidate", "Asset Gate", "Badcase"],
        "judge_entrypoint": "submit_candidate -> existing Java/Maven judge/report path",
        "reuse_refs": [
            "docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md",
            "docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md",
        ],
    }
    blueprint.update(overrides)
    return blueprint


def test_judge_skill_blueprint_normalizes_metadata_only_skill_direction():
    normalized = validate_judge_skill_blueprint(_blueprint())

    assert normalized["schema_version"] == JUDGE_SKILL_BLUEPRINT_SCHEMA_VERSION
    assert normalized["name"] == "unit-test-candidate-eval"
    assert normalized["skill_form"] == "codex_skill_blueprint"
    assert normalized["form_policy"]["current_status"] == "design_allowed_metadata_only"
    assert normalized["pillars"] == ["Candidate", "Asset Gate", "Badcase"]
    assert normalized["runtime_authority"] is False
    assert normalized["model_call_allowed"] is False
    assert normalized["external_execution_allowed"] is False
    assert normalized["dependency_install_allowed"] is False
    assert normalized["service_orchestration_allowed"] is False
    assert normalized["auto_accept_allowed"] is False
    assert normalized["auto_merge_allowed"] is False
    assert normalized["verdict_authority"] is False
    assert normalized["trusted_authority"] is False


@pytest.mark.parametrize(
    "field",
    ["name", "trigger", "fallback", "judge_entrypoint"],
)
def test_judge_skill_blueprint_requires_non_empty_core_strings(field):
    with pytest.raises(JudgeSkillBlueprintValidationError, match=field):
        validate_judge_skill_blueprint(_blueprint(**{field: " "}))


@pytest.mark.parametrize(
    "field",
    ["inputs", "steps", "evidence", "red_lines", "output", "verification", "pillars"],
)
def test_judge_skill_blueprint_requires_non_empty_lists(field):
    with pytest.raises(JudgeSkillBlueprintValidationError, match=field):
        validate_judge_skill_blueprint(_blueprint(**{field: []}))


def test_judge_skill_blueprint_requires_core_judge_red_lines():
    with pytest.raises(JudgeSkillBlueprintValidationError, match="NEED_HUMAN_REVIEW"):
        validate_judge_skill_blueprint(_blueprint(red_lines=[
            "trusted=False must remain fixed",
            "no auto-accept",
        ]))

    with pytest.raises(JudgeSkillBlueprintValidationError, match="trusted=False"):
        validate_judge_skill_blueprint(_blueprint(red_lines=[
            "conclusion must remain NEED_HUMAN_REVIEW",
            "no auto-accept",
        ]))


@pytest.mark.parametrize(
    "flag",
    [
        "runtime_authority",
        "model_call_allowed",
        "external_execution_allowed",
        "dependency_install_allowed",
        "service_orchestration_allowed",
        "auto_accept_allowed",
        "auto_merge_allowed",
        "verdict_authority",
        "trusted_authority",
    ],
)
def test_judge_skill_blueprint_rejects_authority_flags(flag):
    with pytest.raises(JudgeSkillBlueprintValidationError, match=flag):
        validate_judge_skill_blueprint(_blueprint(**{flag: True}))


def test_judge_skill_blueprint_rejects_unknown_pillar_and_forbidden_fields():
    with pytest.raises(JudgeSkillBlueprintValidationError, match="unknown pillars"):
        validate_judge_skill_blueprint(_blueprint(pillars=["Prompt Platform"]))

    with pytest.raises(JudgeSkillBlueprintValidationError, match="secret field"):
        validate_judge_skill_blueprint(_blueprint(notes={"api_key": "do-not-store"}))


def test_judge_skill_readiness_plan_summarizes_forms_and_pillars():
    plan = judge_skill_readiness_plan([
        _blueprint(),
        _blueprint(
            name="future-installed-skill",
            skill_form="installed_skill_candidate",
            trigger="A future owner-approved task wants the SOP packaged as a Codex Skill.",
            pillars=["Candidate", "Provenance"],
            judge_entrypoint="existing judge/report path only",
        ),
    ])

    assert plan["plan_version"] == JUDGE_SKILL_READINESS_PLAN_VERSION
    assert plan["total_blueprints"] == 2
    assert plan["ready_for_design_review"] is True
    assert plan["ready_for_skill_install"] is False
    assert plan["by_skill_form"] == {
        "codex_skill_blueprint": 1,
        "installed_skill_candidate": 1,
    }
    assert plan["by_current_status"] == {
        "design_allowed_metadata_only": 1,
        "future_owner_gated": 1,
    }
    assert plan["by_pillar"] == {
        "Candidate": 2,
        "Asset Gate": 1,
        "Badcase": 1,
        "Provenance": 1,
    }
    assert plan["future_owner_gated_blueprints"] == ["future-installed-skill"]
    assert plan["runtime_authority_blueprints"] == []
    assert plan["model_call_blueprints"] == []
    assert plan["external_execution_blueprints"] == []
    assert plan["verdict_authority_blueprints"] == []
    assert plan["trusted_authority_blueprints"] == []


def test_judge_skill_readiness_plan_empty_blocks_review():
    plan = judge_skill_readiness_plan([])

    assert plan["total_blueprints"] == 0
    assert plan["blocking_flags"] == ["skill_blueprint_missing"]
    assert plan["ready_for_design_review"] is False
    assert plan["ready_for_skill_install"] is False


def test_candidate_eval_skill_readiness_plan_is_metadata_only():
    plan = candidate_eval_skill_readiness_plan()

    assert plan["plan_version"] == JUDGE_SKILL_READINESS_PLAN_VERSION
    assert plan["total_blueprints"] == 2
    assert plan["blocking_flags"] == []
    assert plan["ready_for_design_review"] is True
    assert plan["ready_for_skill_install"] is False
    assert plan["by_skill_form"] == {"codex_skill_blueprint": 2}
    assert plan["by_current_status"] == {"design_allowed_metadata_only": 2}
    assert plan["by_pillar"] == {
        "Candidate": 2,
        "Asset Gate": 2,
        "Badcase": 1,
        "Provenance": 1,
    }
    assert {blueprint["name"] for blueprint in plan["blueprints"]} == {
        "unit-test-candidate-eval",
        "junit-api-candidate-report-review",
    }
    assert plan["runtime_authority_blueprints"] == []
    assert plan["model_call_blueprints"] == []
    assert plan["external_execution_blueprints"] == []
    assert plan["verdict_authority_blueprints"] == []
    assert plan["trusted_authority_blueprints"] == []
