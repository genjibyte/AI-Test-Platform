"""Minimal JudgeEvidence projection for the current Java/Maven judge.

This module is intentionally a pure view over existing report facts. It does not
execute candidates, change recommendations, or migrate report/benchmark/ledger schemas.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Optional

SCHEMA_VERSION = "judge_evidence.v1"
DEFAULT_CANDIDATE_KIND = "junit_unit_candidate"
DEFAULT_RUNNER_TOOL = "maven_surefire_jacoco"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _command_summary(command: Any) -> Optional[str]:
    if isinstance(command, str):
        return command
    if isinstance(command, (list, tuple)):
        return " ".join(str(part) for part in command)
    return None


def _failure_type(report: Mapping[str, Any]) -> Optional[str]:
    if report.get("passed") is True:
        return None
    outcome = report.get("gen_outcome")
    if outcome:
        return str(outcome)
    build_outcome = report.get("build_outcome")
    if build_outcome:
        return str(build_outcome)
    if report.get("compiled") is False:
        return "COMPILE_FAILURE"
    if report.get("executed") is False:
        return "NOT_EXECUTED"
    return None


def _runner_view(execution: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    execution = _mapping(execution)
    exec_record = _mapping(execution.get("exec_record"))
    return {
        "tool": exec_record.get("name") or DEFAULT_RUNNER_TOOL,
        "command_summary": _command_summary(exec_record.get("command")),
        "started_at": exec_record.get("started_at") or None,
        "duration_ms": exec_record.get("duration_ms"),
        "log_path": execution.get("log_path") or exec_record.get("log_path"),
        "timed_out": exec_record.get("timed_out"),
    }


def _quality_view(report: Mapping[str, Any]) -> dict[str, Any]:
    quality = _mapping(report.get("quality_gate"))
    preflight = _mapping(report.get("preflight"))
    return {
        "quality_gate_status": quality.get("status"),
        "quality_checked": quality.get("checked"),
        "blockers": _count(quality.get("blocking_issues")),
        "warnings": _count(quality.get("warnings")),
        "preflight": {
            "status": preflight.get("status"),
            "checked": preflight.get("checked"),
            "blockers": _count(preflight.get("blocking_issues")),
            "warnings": _count(preflight.get("warnings")),
        },
        "review_recommendation": report.get("review_recommendation"),
    }


def _asset_view(report: Mapping[str, Any]) -> dict[str, Any]:
    review_summary = _mapping(report.get("review_summary"))
    asset_sufficiency = _mapping(review_summary.get("asset_sufficiency"))
    test_level_router = _mapping(review_summary.get("test_level_router"))
    return {
        "asset_sufficiency": {
            "test_level_recommendation": asset_sufficiency.get("test_level_recommendation"),
            "code_context": asset_sufficiency.get("code_context"),
            "existing_tests": asset_sufficiency.get("existing_tests"),
            "business_oracle": asset_sufficiency.get("business_oracle"),
            "test_data": asset_sufficiency.get("test_data"),
            "api_schema": asset_sufficiency.get("api_schema"),
            "db_schema": asset_sufficiency.get("db_schema"),
            "external_dependency_mock": asset_sufficiency.get("external_dependency_mock"),
            "missing_assets": deepcopy(_list(asset_sufficiency.get("missing_assets"))),
            "risk_notes": deepcopy(_list(asset_sufficiency.get("risk_notes"))),
            "advisory": asset_sufficiency.get("advisory"),
        },
        "test_level_router": {
            "recommended_level": test_level_router.get("recommended_level"),
            "current_kernel_support": test_level_router.get("current_kernel_support"),
            "owner_gate_required": test_level_router.get("owner_gate_required"),
            "report_only": test_level_router.get("report_only"),
            "advisory": test_level_router.get("advisory"),
            "reason_codes": deepcopy(_list(test_level_router.get("reason_codes"))),
        },
    }


def build_judge_evidence_from_report(
    report: Mapping[str, Any],
    *,
    execution: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Project an assembled report into the minimal JudgeEvidence view.

    ``execution`` is optional because older report callers only have the assembled
    report. When a generation bundle is available, pass its raw execution block to
    surface runner command/log facts without changing the report schema.
    """
    report = _mapping(report)
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_kind": report.get("candidate_kind") or DEFAULT_CANDIDATE_KIND,
        "runner": _runner_view(execution),
        "outcome": {
            "compiled": report.get("compiled"),
            "executed": report.get("executed"),
            "passed": report.get("passed"),
            "failure_type": _failure_type(report),
            "gen_outcome": report.get("gen_outcome"),
            "build_outcome": report.get("build_outcome"),
            "counts": deepcopy(_mapping(report.get("gen_counts"))),
        },
        "quality": _quality_view(report),
        "assets": _asset_view(report),
        "coverage": deepcopy(report.get("coverage_delta")),
        "provenance": {
            "producer_id": report.get("producer_id"),
            "run_kind": report.get("run_kind"),
            "model": report.get("model"),
        },
        "report": {
            "conclusion": report.get("conclusion"),
            "trusted": bool(report.get("trusted", False)),
        },
        "error": report.get("error"),
    }


def build_judge_evidence_from_generation(generation: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble the current report, then project it into JudgeEvidence.

    Kept as a thin convenience wrapper so S6 can prove the contract over the existing
    generation bundle without making the report itself carry a new top-level field.
    """
    from app.report.generation_report import assemble_generation_report

    generation = _mapping(generation)
    report = assemble_generation_report(dict(generation))
    return build_judge_evidence_from_report(
        report,
        execution=_mapping(generation.get("execution")),
    )
