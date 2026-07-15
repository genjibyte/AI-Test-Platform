"""Tests for the minimal JudgeEvidence projection (docs/60_api_candidate/01)."""
from __future__ import annotations

from copy import deepcopy

from app.report.generation_report import CONCLUSION, assemble_generation_report
from app.report.judge_evidence import (
    DEFAULT_CANDIDATE_KIND,
    SCHEMA_VERSION,
    build_judge_evidence_from_generation,
    build_judge_evidence_from_report,
)


def _grounded_bundle(**overrides):
    source = (
        "package com.example;\n"
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.assertEquals;\n\n"
        "class CalcSubmittedTest {\n"
        "  @Test void maxReturnsLargerInput() {\n"
        "    assertEquals(9, new Calc().max(2, 9));\n"
        "  }\n"
        "}\n"
    )
    bundle = {
        "target": {"target_class": "com.example.Calc", "target_method": "max"},
        "result": {
            "test_class_name": "CalcSubmittedTest",
            "test_source": source,
            "behavior_sources": ["Calc.max returns the larger input"],
            "model": "external-codex",
            "producer_id": "external-codex",
            "trusted": False,
        },
        "write": {
            "file_path": "src/test/java/com/example/CalcSubmittedTest.java",
            "created": True,
            "production_code_touched": False,
            "content": source,
        },
        "execution": {
            "gen_outcome": "PASS",
            "build_outcome": "SUCCESS",
            "gen_total": 1,
            "gen_passed": 1,
            "gen_failed": 0,
            "gen_errors": 0,
            "gen_skipped": 0,
            "log_path": "var/jobs/job-1/mvn.log",
            "exec_record": {
                "name": "mvn-test-jacoco",
                "command": ["mvn", "-B", "test"],
                "cwd": "workspace/job-1/repo",
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 1234,
                "log_path": "var/jobs/job-1/mvn.log",
                "started_at": "2026-07-11T00:00:00Z",
                "finished_at": "2026-07-11T00:00:01Z",
            },
        },
        "coverage_delta": {
            "overall_line_delta": 0.1,
            "overall_branch_delta": 0.0,
            "target_line_delta": 0.5,
            "target_branch_delta": 0.0,
            "coverage_dropped": False,
            "target_improved": True,
            "overall_before": {},
            "overall_after": {},
            "target_before": {},
            "target_after": {},
        },
        "run_kind": "external",
        "producer_id": "external-codex",
        "producer_meta": {},
        "error": None,
    }
    bundle.update(overrides)
    return bundle


def test_generation_bundle_projects_to_minimal_judge_evidence_without_mutation():
    bundle = _grounded_bundle()
    before = deepcopy(bundle)

    evidence = build_judge_evidence_from_generation(bundle)

    assert bundle == before
    assert evidence["schema_version"] == SCHEMA_VERSION
    assert evidence["candidate_kind"] == DEFAULT_CANDIDATE_KIND
    assert evidence["runner"] == {
        "tool": "mvn-test-jacoco",
        "command_summary": "mvn -B test",
        "started_at": "2026-07-11T00:00:00Z",
        "duration_ms": 1234,
        "log_path": "var/jobs/job-1/mvn.log",
        "timed_out": False,
    }
    assert evidence["outcome"]["compiled"] is True
    assert evidence["outcome"]["executed"] is True
    assert evidence["outcome"]["passed"] is True
    assert evidence["outcome"]["failure_type"] is None
    assert evidence["outcome"]["counts"]["passed"] == 1
    assert evidence["quality"]["quality_gate_status"] == "PASS"
    assert evidence["assets"]["test_level_router"]["recommended_level"] == "unit"
    assert evidence["assets"]["test_level_router"]["current_kernel_support"] == "supported"
    assert evidence["assets"]["test_level_router"]["report_only"] is True
    assert evidence["provenance"] == {
        "producer_id": "external-codex",
        "run_kind": "external",
        "model": "external-codex",
    }
    assert evidence["report"] == {
        "conclusion": CONCLUSION,
        "trusted": False,
    }


def test_judge_evidence_preserves_failure_as_evidence_not_verdict():
    bundle = _grounded_bundle(
        execution={
            "gen_outcome": "COMPILE_FAILURE",
            "build_outcome": "COMPILE_FAILURE",
            "gen_total": 0,
            "gen_passed": 0,
            "gen_failed": 0,
            "gen_errors": 0,
            "gen_skipped": 0,
        },
    )

    evidence = build_judge_evidence_from_generation(bundle)

    assert evidence["outcome"]["compiled"] is False
    assert evidence["outcome"]["executed"] is False
    assert evidence["outcome"]["passed"] is False
    assert evidence["outcome"]["failure_type"] == "COMPILE_FAILURE"
    assert evidence["report"]["conclusion"] == "NEED_HUMAN_REVIEW"
    assert evidence["report"]["trusted"] is False


def test_report_projection_does_not_copy_full_patch_or_test_source():
    report = assemble_generation_report(_grounded_bundle())

    evidence = build_judge_evidence_from_report(report)
    serialized = str(evidence)

    assert evidence["runner"]["tool"] == "maven_surefire_jacoco"
    assert "patch" not in evidence
    assert "assertEquals(9, new Calc().max(2, 9))" not in serialized
    assert evidence["coverage"]["target_improved"] is True
    assert evidence["report"]["conclusion"] == CONCLUSION
