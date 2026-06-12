"""Oracle-strength estimate tests (docs/46 S1). Offline.

The estimate is an ADVISORY, STRUCTURAL roll-up of quality-gate facts -- never semantic
proof, never a verdict. It reuses the gate's issue codes/metrics (no new parser).
"""
from app.quality.oracle_strength import ORACLE_STRENGTHS, estimate_oracle_strength
from app.quality.test_quality_gate import evaluate_test_quality


def _gate(blocking=(), warnings=(), checked=True, metrics=None):
    return {
        "checked": checked,
        "status": "FAIL" if blocking else ("REVIEW" if warnings else "PASS"),
        "blocking_issues": [{"code": c} for c in blocking],
        "warnings": [{"code": c} for c in warnings],
        "metrics": metrics or {},
    }


def test_levels_from_issue_codes():
    assert estimate_oracle_strength(_gate(blocking=["no_assertions"]))["oracle_strength"] == "none"
    assert estimate_oracle_strength(_gate(blocking=["no_test_methods"]))["oracle_strength"] == "none"
    assert estimate_oracle_strength(_gate(blocking=["only_weak_assertions"]))["oracle_strength"] == "weak"
    assert estimate_oracle_strength(_gate(blocking=["tautological_assertion"]))["oracle_strength"] == "weak"
    assert estimate_oracle_strength(_gate(warnings=["weak_assertion_heavy"]))["oracle_strength"] == "mixed"
    assert estimate_oracle_strength(_gate())["oracle_strength"] == "structural_ok"


def test_unchecked_or_empty_is_unknown():
    assert estimate_oracle_strength(None)["oracle_strength"] == "unknown"
    assert estimate_oracle_strength({"checked": False})["oracle_strength"] == "unknown"


def test_estimate_is_advisory_and_never_semantic():
    est = estimate_oracle_strength(_gate(
        warnings=["missing_behavior_sources"],
        metrics={"assertions": 3, "weak_assertions": 0, "tautological_assertions": 0},
    ))
    assert est["oracle_strength"] == "structural_ok"        # caveat does not lower the level
    assert "missing_behavior_sources" in est["reasons"]     # but is carried for the human
    assert est["semantic_strength"] == "human_review"       # never auto-decided
    assert est["advisory"] is True
    assert est["metrics"]["assertions"] == 3
    assert est["oracle_strength"] in ORACLE_STRENGTHS


def test_none_beats_weak_beats_mixed_precedence():
    # if several signals co-occur, the worst (most cautious) level wins
    est = estimate_oracle_strength(_gate(
        blocking=["no_assertions", "only_weak_assertions"], warnings=["weak_assertion_heavy"]))
    assert est["oracle_strength"] == "none"


def test_estimate_over_real_gate_structural_ok():
    src = (
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.*;\n"
        "class CalcTest {\n"
        "  @Test void adds() { assertEquals(2, new Calc().add(1, 1)); }\n"
        "}\n"
    )
    gate = evaluate_test_quality(src, execution={"gen_outcome": "PASS"}).model_dump()
    est = estimate_oracle_strength(gate)
    assert est["oracle_strength"] == "structural_ok"        # a real assertEquals
    assert est["semantic_strength"] == "human_review"


def test_estimate_over_real_gate_weak_when_only_assert_not_null():
    src = (
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.*;\n"
        "class CalcTest {\n"
        "  @Test void runs() { assertNotNull(new Calc()); }\n"
        "}\n"
    )
    gate = evaluate_test_quality(src, execution={"gen_outcome": "PASS"}).model_dump()
    # assertNotNull only -> gate flags only_weak_assertions -> estimate "weak"
    assert estimate_oracle_strength(gate)["oracle_strength"] == "weak"
