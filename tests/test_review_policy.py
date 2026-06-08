"""Phase 4 review policy tests (docs/22). Deterministic, advisory, never accepts."""
from app.review.review_policy import (
    NEEDS_REVISION,
    REJECT_CANDIDATE,
    REVIEW_CANDIDATE,
    STRONG_REVIEW_CANDIDATE,
    build_review_summary,
    recommend,
    recommend_with_reasons,
)


def test_recommend_rejects_production_code_touch():
    assert recommend(quality_status="PASS", gen_outcome="PASS",
                     production_code_touched=True) == REJECT_CANDIDATE


def test_recommend_rejects_quality_fail():
    assert recommend(quality_status="FAIL", gen_outcome="COMPILE_FAILURE",
                     production_code_touched=False) == REJECT_CANDIDATE


def test_recommend_needs_revision_on_test_failure():
    # compiled + ran but assertions failed -> human decides oracle vs bug.
    assert recommend(quality_status="REVIEW", gen_outcome="TEST_FAILURE",
                     production_code_touched=False) == NEEDS_REVISION


def test_recommend_review_on_quality_review():
    assert recommend(quality_status="REVIEW", gen_outcome="PASS",
                     production_code_touched=False) == REVIEW_CANDIDATE


def test_recommend_strong_on_pass():
    assert recommend(quality_status="PASS", gen_outcome="PASS",
                     production_code_touched=False) == STRONG_REVIEW_CANDIDATE


def test_recommend_conservative_fallback():
    # unexpected combo -> never STRONG, fall back to REVIEW_CANDIDATE.
    assert recommend(quality_status="PASS", gen_outcome="NO_TESTS",
                     production_code_touched=False) == REVIEW_CANDIDATE


FQCN = "org.apache.commons.csv.CSVRecordAiGeneratedTest"


def _generation(failed_cases):
    return {
        "target": {"target_class": "org.apache.commons.csv.CSVRecord",
                   "target_method": None},
        "result": {"test_class_name": "CSVRecordAiGeneratedTest",
                   "behavior_sources": ["neighbor testGet"],
                   "risk_flags": ["assumed exception type"],
                   "omitted_uncertain_cases": ["serialization"],
                   "trusted": False},
        "write": {"file_path": "src/test/java/.../CSVRecordAiGeneratedTest.java",
                  "created": True, "production_code_touched": False},
        "execution": {
            "gen_outcome": "TEST_FAILURE",
            "generated_class": FQCN,
            "suite_result": {"failed_cases": failed_cases},
        },
    }


def test_summary_parses_expected_actual_for_assertion_failure():
    gen = _generation([
        {"classname": FQCN, "name": "testGetIntTooLarge", "type": "failure",
         "message": "Unexpected exception type thrown, expected: "
                    "<java.lang.IllegalArgumentException> but was: "
                    "<java.lang.ArrayIndexOutOfBoundsException>"},
        # a different class's failure must be ignored
        {"classname": "com.other.OtherTest", "name": "x", "type": "failure",
         "message": "expected: <1> but was: <2>"},
    ])
    s = build_review_summary(generation=gen, quality={"status": "REVIEW"},
                             recommendation=NEEDS_REVISION)
    assert s["conclusion"] == "NEED_HUMAN_REVIEW"          # never auto-accept
    assert len(s["failures"]) == 1                         # only the generated class
    f = s["failures"][0]
    assert f["test_name"] == "testGetIntTooLarge"
    assert f["expected"] == "java.lang.IllegalArgumentException"
    assert f["actual"] == "java.lang.ArrayIndexOutOfBoundsException"


def test_summary_uses_message_as_actual_for_exception_error():
    gen = _generation([
        {"classname": FQCN, "name": "testAddValue", "type": "error",
         "message": "The addValue method is not intended for client use."},
    ])
    s = build_review_summary(generation=gen, quality={"status": "REVIEW"},
                             recommendation=NEEDS_REVISION)
    f = s["failures"][0]
    assert f["type"] == "error"
    assert f["expected"] is None
    assert f["actual"] == "The addValue method is not intended for client use."


def test_summary_carries_quality_grounding_and_invariants():
    gen = _generation([])
    s = build_review_summary(
        generation=gen,
        quality={"status": "REVIEW", "warnings": [{"code": "test_failure"}],
                 "advisories": [{"code": "model_declared_risk"}]},
        recommendation=NEEDS_REVISION,
    )
    assert s["recommendation"] == NEEDS_REVISION
    assert s["recommendation_reasons"] == []          # default when none passed
    assert s["quality"]["warnings"] == ["test_failure"]
    assert s["quality"]["advisories"] == ["model_declared_risk"]
    assert s["grounding"]["risk_flags"] == ["assumed exception type"]
    assert s["invariants"] == {
        "trusted": False,
        "production_code_touched": False,
        "auto_accept_blocked": True,            # explicit never-auto-accept fact
    }


# --- risk-aware, explainable recommendation (docs/22) ----------------------------

def test_recommend_with_reasons_clean_pass_is_strong():
    rec, reasons = recommend_with_reasons(
        quality_status="PASS", gen_outcome="PASS", production_code_touched=False)
    assert rec == STRONG_REVIEW_CANDIDATE
    assert reasons == ["clean_pass"]


def test_downgrade_strong_when_machine_repaired():
    rec, reasons = recommend_with_reasons(
        quality_status="PASS", gen_outcome="PASS", production_code_touched=False,
        repair_applied=True)
    assert rec == REVIEW_CANDIDATE
    assert "machine_repaired" in reasons and "downgraded_from_strong" in reasons


def test_downgrade_strong_when_model_declared_risk():
    rec, reasons = recommend_with_reasons(
        quality_status="PASS", gen_outcome="PASS", production_code_touched=False,
        model_risk=True)
    assert rec == REVIEW_CANDIDATE
    assert "model_declared_risk" in reasons and "downgraded_from_strong" in reasons


def test_risk_signal_annotates_non_strong_without_downgrade_marker():
    # quality REVIEW is already below STRONG: signal is recorded, no downgrade marker.
    rec, reasons = recommend_with_reasons(
        quality_status="REVIEW", gen_outcome="PASS", production_code_touched=False,
        repair_applied=True)
    assert rec == REVIEW_CANDIDATE
    assert "machine_repaired" in reasons
    assert "downgraded_from_strong" not in reasons


def test_recommend_string_wrapper_is_backcompat():
    assert recommend(quality_status="PASS", gen_outcome="PASS",
                     production_code_touched=False) == STRONG_REVIEW_CANDIDATE


def test_summary_carries_recommendation_reasons():
    s = build_review_summary(
        generation=_generation([]),
        quality={"status": "PASS"},
        recommendation=REVIEW_CANDIDATE,
        recommendation_reasons=["clean_pass", "machine_repaired",
                                "downgraded_from_strong"],
    )
    assert s["recommendation_reasons"] == [
        "clean_pass", "machine_repaired", "downgraded_from_strong"]
    assert s["invariants"]["auto_accept_blocked"] is True
