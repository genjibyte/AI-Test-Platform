from app.quality.test_quality_gate import evaluate_test_quality


GOOD_TEST = """
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class CalcAiGeneratedTest {
    @Test
    void maxReturnsLargerInput() {
        assertEquals(5, new Calc().max(3, 5));
    }
}
"""


def test_quality_gate_passes_meaningful_grounded_test():
    result = evaluate_test_quality(
        GOOD_TEST,
        execution={"gen_outcome": "PASS"},
        target_class="com.example.Calc",
        target_method="max",
        grounding={"behavior_sources": ["Calc.max compares the two inputs"]},
    )
    assert result.status == "PASS"
    assert result.metrics["assertions"] == 1
    assert result.blocking_issues == []


def test_quality_gate_blocks_no_assertions():
    result = evaluate_test_quality(
        "class T { @Test void noop() { new Calc().max(1, 2); } }",
        execution={"gen_outcome": "PASS"},
        target_class="com.example.Calc",
        target_method="max",
    )
    codes = {i.code for i in result.blocking_issues}
    assert result.status == "FAIL"
    assert "no_assertions" in codes


def test_quality_gate_blocks_only_weak_assertions():
    result = evaluate_test_quality(
        "class T { @Test void weak() { assertNotNull(new Calc()); } }",
        execution={"gen_outcome": "PASS"},
        target_class="com.example.Calc",
    )
    codes = {i.code for i in result.blocking_issues}
    assert result.status == "FAIL"
    assert "only_weak_assertions" in codes


def test_quality_gate_blocks_tautological_assertions():
    result = evaluate_test_quality(
        "class T { @Test void tautology() { int x = 1; assertEquals(x, x); } }",
        execution={"gen_outcome": "PASS"},
    )
    codes = {i.code for i in result.blocking_issues}
    assert result.status == "FAIL"
    assert "tautological_assertion" in codes


def test_quality_gate_does_not_collapse_distinct_string_literals():
    result = evaluate_test_quality(
        'class T { @Test void strings() { assertEquals("expected", "actual"); } }',
        execution={"gen_outcome": "PASS"},
        grounding={"behavior_sources": ["string behavior"]},
    )
    codes = {i.code for i in result.blocking_issues}
    assert "tautological_assertion" not in codes


def test_quality_gate_ignores_comment_noise_for_unstable_apis():
    result = evaluate_test_quality(
        """
        class T {
            // Avoid Thread.sleep, URL, and file APIs in generated tests.
            /* Also avoid Paths.get("tmp") in real test code. */
            @Test void stable() {
                assertEquals(2, new Calc().max(1, 2));
            }
        }
        """,
        execution={"gen_outcome": "PASS"},
        target_class="com.example.Calc",
        target_method="max",
        grounding={"behavior_sources": ["Calc.max returns the larger input"]},
    )
    codes = {i.code for i in result.blocking_issues}
    assert "thread_sleep" not in codes
    assert "external_io" not in codes
    assert result.status == "PASS"


def test_quality_gate_blocks_unstable_and_internal_access():
    result = evaluate_test_quality(
        """
        class T {
            @Test void unstable() throws Exception {
                Thread.sleep(1);
                Calc.class.getDeclaredField("value").setAccessible(true);
                assertEquals(1, 1 + 0);
            }
        }
        """,
        execution={"gen_outcome": "PASS"},
    )
    codes = {i.code for i in result.blocking_issues}
    assert result.status == "FAIL"
    assert "thread_sleep" in codes
    assert "internal_implementation_access" in codes


def test_quality_gate_warns_when_oracle_sources_missing():
    result = evaluate_test_quality(
        GOOD_TEST,
        execution={"gen_outcome": "PASS"},
        target_class="com.example.Calc",
        target_method="max",
    )
    codes = {i.code for i in result.warnings}
    assert result.status == "REVIEW"
    assert "missing_behavior_sources" in codes


PARAMETERIZED_TEST = """
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CalcAiGeneratedTest {
    @ParameterizedTest
    @ValueSource(ints = {1, 2, 3})
    void positiveStaysPositive(int n) {
        assertTrue(new Calc().max(n, 0) > 0);
    }
}
"""


def test_quality_gate_counts_junit5_parameterized_tests():
    # FP fix: a parameterized test is a real test, not "no @Test methods".
    result = evaluate_test_quality(
        PARAMETERIZED_TEST,
        execution={"gen_outcome": "PASS"},
        target_class="com.example.Calc",
        grounding={"behavior_sources": ["max keeps a positive input positive"]},
    )
    codes = {i.code for i in result.blocking_issues}
    assert "no_test_methods" not in codes
    assert result.metrics["test_methods"] == 1
    assert result.status != "FAIL"


def test_model_declared_risk_is_advisory_not_a_downgrade():
    # FP fix: an honest, benign risk_flag must not drop a clean test to REVIEW.
    result = evaluate_test_quality(
        GOOD_TEST,
        execution={"gen_outcome": "PASS"},
        target_class="com.example.Calc",
        target_method="max",
        grounding={
            "behavior_sources": ["Calc.max compares the two inputs"],
            "risk_flags": ["No mocks used; all tests use real instances."],
        },
    )
    assert result.status == "PASS"                       # not downgraded
    warn_codes = {i.code for i in result.warnings}
    adv_codes = {i.code for i in result.advisories}
    assert "model_declared_risk" not in warn_codes       # not a warning
    assert "model_declared_risk" in adv_codes            # still surfaced to reviewer


def test_genuine_quality_warning_still_downgrades():
    # A real test-quality concern (weak-assertion-heavy) must still force REVIEW,
    # even though risk_flags are now advisory.
    src = (
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.*;\n"
        "class T {\n"
        "  @Test void m() {\n"
        "    Calc c = new Calc();\n"
        "    assertNotNull(c); assertNotNull(c); assertNotNull(c);\n"
        "    assertEquals(5, c.max(3, 5));\n"
        "  }\n"
        "}\n"
    )
    result = evaluate_test_quality(
        src, execution={"gen_outcome": "PASS"}, target_class="com.example.Calc",
        grounding={"behavior_sources": ["max"], "risk_flags": ["all real instances"]},
    )
    assert result.status == "REVIEW"
    assert "weak_assertion_heavy" in {i.code for i in result.warnings}
