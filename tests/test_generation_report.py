"""Tests for generation report assembly (P2-T09)."""
from app.report.generation_report import CONCLUSION, assemble_generation_report


def _bundle(**over):
    b = {
        "target": {"target_class": "com.example.Calc", "target_method": "max"},
        "result": {
            "test_class_name": "CalcAiGeneratedTest",
            "test_source": "class CalcAiGeneratedTest {}",
            "scenarios": ["happy", "edge"],
            "mocks": [],
            "model": "fake-1",
            "trusted": False,
        },
        "write": {
            "file_path": "src/test/java/com/example/CalcAiGeneratedTest.java",
            "created": True,
            "production_code_touched": False,
            "content": "package com.example;\nclass CalcAiGeneratedTest {}\n",
        },
        "execution": {
            "gen_outcome": "PASS",
            "build_outcome": "SUCCESS",
            "gen_total": 2, "gen_passed": 2, "gen_failed": 0,
            "gen_errors": 0, "gen_skipped": 0,
        },
        "coverage_delta": {
            "overall_line_delta": 0.2, "overall_branch_delta": 0.5,
            "target_line_delta": 0.2, "target_branch_delta": 0.5,
            "coverage_dropped": False, "target_improved": True,
            "overall_before": {}, "overall_after": {},
            "target_before": {}, "target_after": {},
        },
        "error": None,
    }
    b.update(over)
    return b


def test_pass_report_shape():
    r = assemble_generation_report(_bundle())
    assert r["generated"] and r["compiled"] and r["executed"] and r["passed"]
    assert r["test_file"].endswith("CalcAiGeneratedTest.java")
    assert r["gen_counts"]["passed"] == 2
    assert r["coverage_delta"]["target_improved"] is True
    assert r["patch"]["is_new_file"] is True
    assert "class CalcAiGeneratedTest" in r["patch"]["content"]


def test_conclusion_is_always_human_review():
    # Even a clean PASS must NOT auto-accept in Phase 2.
    assert assemble_generation_report(_bundle())["conclusion"] == CONCLUSION
    assert CONCLUSION == "NEED_HUMAN_REVIEW"


def test_invariants_never_trusted_or_prod_touched():
    r = assemble_generation_report(_bundle())
    assert r["trusted"] is False
    assert r["production_code_touched"] is False


def test_v2_grounding_metadata_surfaces_for_human_review():
    bundle = _bundle()
    bundle["result"].update({
        "used_apis": ["Calc.max"],
        "behavior_sources": ["Calc.max source branch a > b"],
        "omitted_uncertain_cases": ["overflow behavior"],
        "risk_flags": ["none"],
        "dependency_assumptions": ["JUnit5 assertions"],
    })
    r = assemble_generation_report(bundle)
    assert r["grounding"]["used_apis"] == ["Calc.max"]
    assert r["grounding"]["behavior_sources"] == ["Calc.max source branch a > b"]
    assert r["grounding"]["omitted_uncertain_cases"] == ["overflow behavior"]
    assert r["grounding"]["risk_flags"] == ["none"]
    assert r["grounding"]["dependency_assumptions"] == ["JUnit5 assertions"]


def test_phase3_repair_trace_surfaces_for_human_review():
    bundle = _bundle()
    bundle["repair"] = {
        "enabled": True,
        "repair_rounds": 1,
        "final_outcome": "PASS",
        "rounds": [{
            "round": 1,
            "changed": True,
            "patches": [{"bucket": "missing_static_import"}],
            "before_outcome": "COMPILE_FAILURE",
            "after_outcome": "PASS",
        }],
    }
    r = assemble_generation_report(bundle)
    assert r["repair"]["enabled"] is True
    assert r["repair"]["repair_rounds"] == 1
    assert r["repair"]["final_outcome"] == "PASS"
    assert r["repair"]["rounds"][0]["before_outcome"] == "COMPILE_FAILURE"


def test_quality_gate_surfaces_deterministic_findings():
    r = assemble_generation_report(_bundle())
    assert r["quality_gate"]["checked"] is True
    assert r["quality_gate"]["status"] == "FAIL"
    codes = {i["code"] for i in r["quality_gate"]["blocking_issues"]}
    assert "no_test_methods" in codes
    assert "no_assertions" in codes


def test_quality_gate_can_pass_a_grounded_meaningful_test():
    bundle = _bundle()
    source = (
        "package com.example;\n"
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.assertEquals;\n\n"
        "class CalcAiGeneratedTest {\n"
        "  @Test void maxReturnsLargerInput() {\n"
        "    assertEquals(9, new Calc().max(2, 9));\n"
        "  }\n"
        "}\n"
    )
    bundle["result"]["test_source"] = source
    bundle["result"]["behavior_sources"] = ["Calc.max returns the larger input"]
    bundle["write"]["content"] = source
    r = assemble_generation_report(bundle)
    assert r["quality_gate"]["status"] == "PASS"
    assert r["quality_gate"]["metrics"]["assertions"] == 1


def test_compile_failure_not_compiled_not_executed():
    r = assemble_generation_report(
        _bundle(execution={"gen_outcome": "COMPILE_FAILURE",
                           "build_outcome": "COMPILE_FAILURE"})
    )
    assert r["compiled"] is False
    assert r["executed"] is False
    assert r["passed"] is False
    assert r["conclusion"] == CONCLUSION  # failures still surface, not hidden


def test_test_failure_compiled_executed_not_passed():
    r = assemble_generation_report(
        _bundle(execution={"gen_outcome": "TEST_FAILURE", "build_outcome":
                           "TEST_FAILURE", "gen_total": 1, "gen_failed": 1})
    )
    assert r["compiled"] is True
    assert r["executed"] is True
    assert r["passed"] is False


def test_no_tests_compiled_but_not_executed():
    r = assemble_generation_report(
        _bundle(execution={"gen_outcome": "NO_TESTS", "build_outcome": "SUCCESS"})
    )
    assert r["compiled"] is True
    assert r["executed"] is False


def test_error_is_surfaced_not_hidden():
    r = assemble_generation_report(_bundle(error="context collection failed"))
    assert r["error"] == "context collection failed"


def test_empty_bundle_degrades_gracefully():
    r = assemble_generation_report({})
    assert r["generated"] is False
    assert r["conclusion"] == CONCLUSION
    assert r["compiled"] is False
