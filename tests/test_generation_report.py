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


def test_preflight_findings_surface_in_report_and_review_summary():
    bundle = _bundle()
    bundle["preflight"] = {
        "checked": True,
        "status": "FAIL",
        "blocking_issues": [{
            "code": "unlisted_target_overload_arity",
            "severity": "blocker",
            "message": "target-class call arity is not in the rendered method list",
            "evidence": "Calc.missing(1, 2)",
        }],
        "metrics": {"target_class_calls": 1},
    }
    bundle["execution"] = {
        "gen_outcome": "COMPILE_FAILURE",
        "build_outcome": "PREFLIGHT_REJECT",
    }
    r = assemble_generation_report(bundle)
    assert r["preflight"]["status"] == "FAIL"
    assert r["preflight"]["blocking_issues"][0]["code"] == (
        "unlisted_target_overload_arity"
    )
    assert r["review_summary"]["preflight"]["blockers"][0]["evidence"] == (
        "Calc.missing(1, 2)"
    )


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


# --- risk-aware, explainable review recommendation (docs/22) ---------------------

def _grounded_pass_bundle(**over):
    """A quality-PASS + gen-PASS bundle whose base recommendation is STRONG."""
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
    b = _bundle()
    b["result"]["test_source"] = source
    b["result"]["behavior_sources"] = ["Calc.max returns the larger input"]
    b["write"]["content"] = source
    b.update(over)
    return b


def test_clean_pass_is_strong_with_reasons_and_invariant():
    r = assemble_generation_report(_grounded_pass_bundle())
    assert r["review_recommendation"] == "STRONG_REVIEW_CANDIDATE"
    rs = r["review_summary"]
    assert rs["recommendation_reasons"] == ["clean_pass"]
    assert rs["invariants"]["auto_accept_blocked"] is True
    # docs/46 S1: the advisory structural oracle-strength estimate surfaces here
    assert rs["oracle_strength_estimate"]["oracle_strength"] == "structural_ok"
    assert rs["oracle_strength_estimate"]["semantic_strength"] == "human_review"
    # docs/55 S1/S2: asset sufficiency is advisory and does not alter the clean-pass triage.
    assert rs["asset_sufficiency"]["business_oracle"] == "sufficient"
    assert rs["asset_sufficiency"]["test_level_recommendation"] == "unit"
    # docs/55 S4A: report-only router surfaces current support without changing verdicts.
    assert rs["test_level_router"]["recommended_level"] == "unit"
    assert rs["test_level_router"]["current_kernel_support"] == "supported"
    assert rs["test_level_router"]["owner_gate_required"] is False
    assert rs["test_level_router"]["report_only"] is True
    assert rs["test_level_router"]["advisory"] is True
    assert r["conclusion"] == CONCLUSION
    assert r["trusted"] is False


def test_machine_repaired_pass_downgrades_from_strong():
    bundle = _grounded_pass_bundle()
    bundle["repair"] = {"enabled": True, "repair_rounds": 1,
                        "final_outcome": "PASS", "rounds": []}
    r = assemble_generation_report(bundle)
    assert r["review_recommendation"] == "REVIEW_CANDIDATE"
    reasons = r["review_summary"]["recommendation_reasons"]
    assert "machine_repaired" in reasons and "downgraded_from_strong" in reasons


def test_model_declared_risk_downgrades_from_strong():
    bundle = _grounded_pass_bundle()
    bundle["result"]["risk_flags"] = ["assumed exception type"]
    r = assemble_generation_report(bundle)
    assert r["review_recommendation"] == "REVIEW_CANDIDATE"
    assert "model_declared_risk" in r["review_summary"]["recommendation_reasons"]


def test_no_risk_sentinel_stays_strong():
    # the benign "none" sentinel must NOT downgrade a clean pass.
    bundle = _grounded_pass_bundle()
    bundle["result"]["risk_flags"] = ["none"]
    r = assemble_generation_report(bundle)
    assert r["review_recommendation"] == "STRONG_REVIEW_CANDIDATE"


def test_asset_sufficiency_surfaces_for_weak_candidate_without_verdict_change():
    r = assemble_generation_report(_bundle())
    rs = r["review_summary"]
    assert rs["asset_sufficiency"]["business_oracle"] == "missing"
    assert rs["asset_sufficiency"]["test_level_recommendation"] == "manual_oracle_first"
    assert rs["test_level_router"]["recommended_level"] == "manual_oracle_first"
    assert rs["test_level_router"]["current_kernel_support"] == "manual_review_required"
    assert rs["test_level_router"]["owner_gate_required"] is True
    assert any(f["signal"] == "asset_sufficiency" for f in rs["digest"]["flags"])
    assert not any(f["signal"] == "test_level_router" for f in rs["digest"]["flags"])
    assert r["conclusion"] == CONCLUSION


def test_test_level_router_treats_provenance_as_context_only():
    bundle = _grounded_pass_bundle(run_kind="external")
    bundle["result"]["producer_id"] = "external-codex"

    r = assemble_generation_report(bundle)
    router = r["review_summary"]["test_level_router"]

    assert router["recommended_level"] == "unit"
    assert router["current_kernel_support"] == "supported"
    assert router["owner_gate_required"] is False
    assert "provenance_is_context_not_proof" in router["reason_codes"]
    assert router["evidence"][1] == {
        "source": "provenance",
        "run_kind": "external",
        "producer_id_present": True,
    }
    assert "external-codex" not in str(router)
    assert r["review_recommendation"] == "STRONG_REVIEW_CANDIDATE"
    assert r["conclusion"] == CONCLUSION
    assert r["trusted"] is False
