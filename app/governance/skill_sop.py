"""Judge Skill/SOP readiness gates.

These helpers treat skillization as reusable operating procedure design for
the existing judge. They do not create, install, invoke, or authorize Codex
Skills, plugins, external tools, model calls, verdict changes, or trusted
status.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Iterable, Mapping

JUDGE_SKILL_BLUEPRINT_SCHEMA_VERSION = "judge_skill_blueprint.v1"
JUDGE_SKILL_READINESS_PLAN_VERSION = "judge_skill_readiness_plan.v1"

_CURRENT_SKILL_STATUS = (
    "Skill/SOP direction is recommended for reusable judge workflows, but "
    "current project usage is metadata/design only. The judge kernel remains "
    "the runtime authority for evidence collection, and reports stay advisory."
)

_ALLOWED_SKILL_FORMS = {
    "sop_template",
    "codex_skill_blueprint",
    "installed_skill_candidate",
}

_ALLOWED_PILLARS = {
    "Candidate",
    "Provenance",
    "Badcase",
    "Asset Gate",
}

_FORM_POLICIES: dict[str, dict[str, Any]] = {
    "sop_template": {
        "current_status": "allowed_now_documentation_only",
        "allowed_now": (
            "write_or_update_sop_template",
            "reference_existing_judge_entrypoint",
            "record_evidence_and_red_lines",
        ),
        "owner_gate_before": (
            "codex_skill_package",
            "agent_workflow",
            "runtime_invocation",
        ),
    },
    "codex_skill_blueprint": {
        "current_status": "design_allowed_metadata_only",
        "allowed_now": (
            "draft_skill_frontmatter_and_body",
            "map_to_existing_sop",
            "validate_no_runtime_authority",
        ),
        "owner_gate_before": (
            "install_skill",
            "enable_auto_trigger",
            "ship_to_agent_runtime",
        ),
    },
    "installed_skill_candidate": {
        "current_status": "future_owner_gated",
        "allowed_now": (),
        "owner_gate_before": (
            "install_skill",
            "invoke_skill_in_project_workflow",
            "bundle_scripts_or_assets",
        ),
    },
}

_REQUIRED_BLUEPRINT_FIELDS = (
    "name",
    "skill_form",
    "trigger",
    "inputs",
    "steps",
    "evidence",
    "red_lines",
    "output",
    "fallback",
    "verification",
    "pillars",
    "judge_entrypoint",
    "reuse_refs",
)

_AUTHORITY_FLAG_FIELDS = (
    "runtime_authority",
    "model_call_allowed",
    "external_execution_allowed",
    "dependency_install_allowed",
    "service_orchestration_allowed",
    "auto_accept_allowed",
    "auto_merge_allowed",
    "verdict_authority",
    "trusted_authority",
)

_OPTIONAL_BLUEPRINT_FIELDS = (
    "schema_version",
    "owner_gate_ref",
    "notes",
) + _AUTHORITY_FLAG_FIELDS

_FORBIDDEN_BLUEPRINT_KEYS = {
    ".env",
    "api_key",
    "authorization",
    "auto_accept",
    "auto_merge",
    "cookie",
    "credentials",
    "database_url",
    "execute_command",
    "install_command",
    "password",
    "raw_payload",
    "raw_request",
    "raw_response",
    "request_body",
    "response_body",
    "secret",
    "service_snapshot",
    "token",
    "trusted",
    "vendor_path",
}


class JudgeSkillBlueprintValidationError(ValueError):
    """Raised when a judge Skill/SOP blueprint violates the readiness gate."""


def validate_judge_skill_blueprint(blueprint: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a Skill/SOP blueprint for safe judge usage.

    A valid blueprint may describe a future Codex Skill shape, but it remains
    metadata only. It must route through existing judge entrypoints and preserve
    `NEED_HUMAN_REVIEW`, `trusted=False`, and command-evidence requirements.
    """
    if not isinstance(blueprint, Mapping):
        raise JudgeSkillBlueprintValidationError(
            "judge skill blueprint must be a mapping"
        )

    _reject_blueprint_forbidden_fields(blueprint)
    _reject_unknown_blueprint_fields(blueprint)

    missing = [field for field in _REQUIRED_BLUEPRINT_FIELDS if field not in blueprint]
    if missing:
        raise JudgeSkillBlueprintValidationError(
            "judge skill blueprint missing required fields: " + ", ".join(missing)
        )

    schema_version = _optional_str(
        blueprint.get("schema_version", JUDGE_SKILL_BLUEPRINT_SCHEMA_VERSION),
        "schema_version",
    )
    if schema_version != JUDGE_SKILL_BLUEPRINT_SCHEMA_VERSION:
        raise JudgeSkillBlueprintValidationError(
            f"unsupported schema_version: {schema_version!r}"
        )

    skill_form = _required_str(blueprint["skill_form"], "skill_form")
    if skill_form not in _ALLOWED_SKILL_FORMS:
        allowed = ", ".join(sorted(_ALLOWED_SKILL_FORMS))
        raise JudgeSkillBlueprintValidationError(
            f"unknown skill_form {skill_form!r}; allowed: {allowed}"
        )

    for flag in _AUTHORITY_FLAG_FIELDS:
        _reject_true_authority_flag(blueprint.get(flag, False), flag)

    red_lines = _string_list(blueprint["red_lines"], "red_lines")
    _require_core_red_lines(red_lines)

    pillars = _string_list(blueprint["pillars"], "pillars")
    unknown_pillars = sorted(set(pillars) - _ALLOWED_PILLARS)
    if unknown_pillars:
        allowed = ", ".join(sorted(_ALLOWED_PILLARS))
        raise JudgeSkillBlueprintValidationError(
            "unknown pillars: " + ", ".join(unknown_pillars) + f"; allowed: {allowed}"
        )

    form_policy = deepcopy(_FORM_POLICIES[skill_form])
    return {
        "schema_version": schema_version,
        "name": _required_str(blueprint["name"], "name"),
        "skill_form": skill_form,
        "trigger": _required_str(blueprint["trigger"], "trigger"),
        "inputs": _string_list(blueprint["inputs"], "inputs"),
        "steps": _string_list(blueprint["steps"], "steps"),
        "evidence": _string_list(blueprint["evidence"], "evidence"),
        "red_lines": red_lines,
        "output": _string_list(blueprint["output"], "output"),
        "fallback": _required_str(blueprint["fallback"], "fallback"),
        "verification": _string_list(blueprint["verification"], "verification"),
        "pillars": pillars,
        "judge_entrypoint": _required_str(
            blueprint["judge_entrypoint"], "judge_entrypoint"
        ),
        "reuse_refs": _string_list(blueprint["reuse_refs"], "reuse_refs"),
        "owner_gate_ref": _optional_str(
            blueprint.get("owner_gate_ref"), "owner_gate_ref"
        ),
        "notes": _optional_str(blueprint.get("notes"), "notes"),
        "form_policy": {
            "current_status": form_policy["current_status"],
            "allowed_now": list(form_policy["allowed_now"]),
            "owner_gate_before": list(form_policy["owner_gate_before"]),
        },
        "runtime_authority": False,
        "model_call_allowed": False,
        "external_execution_allowed": False,
        "dependency_install_allowed": False,
        "service_orchestration_allowed": False,
        "auto_accept_allowed": False,
        "auto_merge_allowed": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "note": (
            "Skill/SOP readiness metadata only. Use Skill direction to reuse "
            "safe judge workflows, not to replace judge evidence, install tools, "
            "call models, execute external systems, or change verdict/trust."
        ),
    }


def judge_skill_readiness_plan(
    blueprints: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate and summarize a batch of Skill/SOP blueprints."""
    normalized = [validate_judge_skill_blueprint(blueprint) for blueprint in blueprints]
    blocking_flags = [] if normalized else ["skill_blueprint_missing"]
    future_owner_gated = [
        blueprint["name"]
        for blueprint in normalized
        if blueprint["form_policy"]["current_status"] == "future_owner_gated"
    ]

    return {
        "plan_version": JUDGE_SKILL_READINESS_PLAN_VERSION,
        "schema_version": JUDGE_SKILL_BLUEPRINT_SCHEMA_VERSION,
        "current_skill_status": _CURRENT_SKILL_STATUS,
        "total_blueprints": len(normalized),
        "by_skill_form": _counter_dict(
            blueprint["skill_form"] for blueprint in normalized
        ),
        "by_current_status": _counter_dict(
            blueprint["form_policy"]["current_status"] for blueprint in normalized
        ),
        "by_pillar": _counter_dict(
            pillar for blueprint in normalized for pillar in blueprint["pillars"]
        ),
        "future_owner_gated_blueprints": future_owner_gated,
        "runtime_authority_blueprints": [
            blueprint["name"]
            for blueprint in normalized
            if blueprint["runtime_authority"] is True
        ],
        "model_call_blueprints": [
            blueprint["name"]
            for blueprint in normalized
            if blueprint["model_call_allowed"] is True
        ],
        "external_execution_blueprints": [
            blueprint["name"]
            for blueprint in normalized
            if blueprint["external_execution_allowed"] is True
        ],
        "verdict_authority_blueprints": [
            blueprint["name"]
            for blueprint in normalized
            if blueprint["verdict_authority"] is True
        ],
        "trusted_authority_blueprints": [
            blueprint["name"]
            for blueprint in normalized
            if blueprint["trusted_authority"] is True
        ],
        "blocking_flags": blocking_flags,
        "ready_for_design_review": not blocking_flags,
        "ready_for_skill_install": False,
        "blueprints": [_compact_blueprint(blueprint) for blueprint in normalized],
        "note": (
            "Readiness plan only. Owner approval is still required before any "
            "Codex Skill package, install, auto-trigger, external execution, "
            "model call, dependency, verdict authority, or trusted status."
        ),
    }


def candidate_eval_skill_readiness_plan() -> dict[str, Any]:
    """Return a metadata-only readiness plan for the first evaluation Skills."""
    return judge_skill_readiness_plan([
        {
            "name": "unit-test-candidate-eval",
            "skill_form": "codex_skill_blueprint",
            "trigger": (
                "A human, agent, or external producer submits a Java/Maven "
                "JUnit or TestNG unit-test candidate for judgment."
            ),
            "inputs": [
                "target_class",
                "target_method if available",
                "test_source",
                "producer_id",
                "producer_meta if available",
            ],
            "steps": [
                "submit through the existing candidate path",
                "let the Java/Maven judge collect compile, Surefire, and coverage evidence",
                "read quality gate, Asset Gate, review digest, conclusion, and trusted fields",
                "summarize observed evidence and advisory review guidance only",
            ],
            "evidence": [
                "judge command or pipeline result",
                "compile/build status",
                "Surefire outcome and counts",
                "quality gate blockers and warnings",
                "review_summary.asset_sufficiency",
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
                "commands and exact result lines cited",
            ],
            "fallback": (
                "If command evidence is missing or contradictory, say the "
                "candidate is unverified and stop."
            ),
            "verification": [
                "run existing offline judge or pytest evidence checks",
                "confirm conclusion and trusted fields are unchanged",
            ],
            "pillars": ["Candidate", "Asset Gate", "Badcase"],
            "judge_entrypoint": "submit_candidate -> existing Java/Maven judge/report path",
            "reuse_refs": [
                "docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md#unit-test-candidate-eval",
                "docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md",
            ],
        },
        {
            "name": "junit-api-candidate-report-review",
            "skill_form": "codex_skill_blueprint",
            "trigger": (
                "A report or bundle explicitly carries candidate_kind=junit_api_candidate "
                "or compact api_evidence."
            ),
            "inputs": [
                "generation report",
                "review_summary.api_evidence if present",
                "api_smoke_manifest.v1 if present",
                "asset_sufficiency if present",
            ],
            "steps": [
                "verify api_evidence is advisory and report-only",
                "check redaction flags and forbidden payload/secret fields",
                "confirm the runner remains maven_surefire_jacoco",
                "report API asset gaps as human-review facts only",
            ],
            "evidence": [
                "review_summary.api_evidence",
                "redaction flags",
                "execution.runner_tool",
                "asset requirement statuses",
                "manifest smoke_id if present",
            ],
            "red_lines": [
                "conclusion must remain NEED_HUMAN_REVIEW",
                "trusted=False must remain fixed",
                "no auto-accept or auto-merge",
                "no API executor, service start, or external tool install",
            ],
            "output": [
                "API evidence summary",
                "asset gaps",
                "redaction status",
                "human-review notes",
            ],
            "fallback": (
                "If api_evidence is absent, evaluate as the existing Java/Maven "
                "path and state that API evidence was not provided."
            ),
            "verification": [
                "run API evidence/report-only tests",
                "confirm no executor, digest severity, verdict, or trust change",
            ],
            "pillars": ["Candidate", "Asset Gate", "Provenance"],
            "judge_entrypoint": "existing report-only junit_api_candidate path",
            "reuse_refs": [
                "docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md#junit-api-candidate-report-review",
                "docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md",
            ],
        },
    ])


def _compact_blueprint(blueprint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": blueprint["name"],
        "skill_form": blueprint["skill_form"],
        "current_status": blueprint["form_policy"]["current_status"],
        "pillars": list(blueprint["pillars"]),
        "judge_entrypoint": blueprint["judge_entrypoint"],
        "runtime_authority": blueprint["runtime_authority"],
        "model_call_allowed": blueprint["model_call_allowed"],
        "external_execution_allowed": blueprint["external_execution_allowed"],
        "verdict_authority": blueprint["verdict_authority"],
        "trusted_authority": blueprint["trusted_authority"],
    }


def _reject_unknown_blueprint_fields(blueprint: Mapping[str, Any]) -> None:
    allowed = set(_REQUIRED_BLUEPRINT_FIELDS) | set(_OPTIONAL_BLUEPRINT_FIELDS)
    unknown = sorted(str(key) for key in blueprint if str(key) not in allowed)
    if unknown:
        raise JudgeSkillBlueprintValidationError(
            "judge skill blueprint has unknown fields: " + ", ".join(unknown)
        )


def _reject_blueprint_forbidden_fields(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_BLUEPRINT_KEYS:
                raise JudgeSkillBlueprintValidationError(
                    "judge skill blueprint must not contain authority, raw "
                    f"payload, command, or secret field: {child_path}"
                )
            _reject_blueprint_forbidden_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_blueprint_forbidden_fields(child, f"{path}[{index}]")


def _reject_true_authority_flag(value: Any, name: str) -> None:
    if not isinstance(value, bool):
        raise JudgeSkillBlueprintValidationError(f"{name} must be boolean")
    if value is True:
        raise JudgeSkillBlueprintValidationError(
            f"{name} must remain false for judge Skill/SOP readiness"
        )


def _required_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JudgeSkillBlueprintValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise JudgeSkillBlueprintValidationError(f"{name} must be a string")
    stripped = value.strip()
    return stripped or None


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise JudgeSkillBlueprintValidationError(f"{name} must be a list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise JudgeSkillBlueprintValidationError(
                f"{name}[{index}] must be a non-empty string"
            )
        normalized.append(item.strip())
    if not normalized:
        raise JudgeSkillBlueprintValidationError(f"{name} must not be empty")
    return normalized


def _require_core_red_lines(red_lines: Iterable[str]) -> None:
    text = " ".join(red_lines).lower()
    compact = (
        text.replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("`", "")
    )
    missing = []
    if "needhumanreview" not in compact:
        missing.append("NEED_HUMAN_REVIEW")
    if "trusted=false" not in compact and "trustedfalse" not in compact:
        missing.append("trusted=False")
    if "noautoaccept" not in compact and "neverautoaccept" not in compact:
        missing.append("no auto-accept")
    if missing:
        raise JudgeSkillBlueprintValidationError(
            "red_lines must preserve: " + ", ".join(missing)
        )


def _counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values).most_common())
