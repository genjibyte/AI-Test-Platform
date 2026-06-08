from app.repair.compile_repair import (
    CompileRepairResult,
    _oracle_signature,
    repair_compile_failure,
    repair_is_safe,
)


def test_adds_missing_junit_static_import():
    src = """package x;

import static org.junit.jupiter.api.Assertions.assertEquals;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { assertSame("a", "a"); }
}
"""
    out = repair_compile_failure(src)
    assert out.changed
    assert "import static org.junit.jupiter.api.Assertions.assertSame;" in out.source
    assert any(p.bucket == "missing_static_import" for p in out.patches)


def test_static_import_added_only_when_compile_log_flags_it():
    src = """package x;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { assertSame("a", "a"); }
}
"""
    log = "X.java:[5,9] 找不到符号\n  符号:   方法 assertSame(java.lang.String,java.lang.String)\n"
    out = repair_compile_failure(src, compile_log=log)
    assert out.changed
    assert "import static org.junit.jupiter.api.Assertions.assertSame;" in out.source


def test_static_import_not_added_when_log_flags_other_symbol():
    # The compile log names a different missing symbol -> the assertSame import,
    # which the compiler did not flag, must NOT be added (log-triggered precision).
    src = """package x;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { assertSame("a", "a"); }
}
"""
    log = "X.java:[5,9] cannot find symbol\n  symbol:   method putInMap(java.util.Map)\n"
    out = repair_compile_failure(src, compile_log=log)
    assert not out.changed
    assert "Assertions.assertSame" not in out.source


def test_keeps_list_of_inside_assertion_oracle():
    # docs/38: List.of inside an assertion is an expected-value (oracle) expression;
    # it must NOT be rewritten, even on Java 8 -- leave the compile error for review.
    src = """package x;

import java.util.List;
import static org.junit.jupiter.api.Assertions.assertEquals;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { assertEquals(List.of("1", "2"), values()); }
}
"""
    out = repair_compile_failure(src, java_source_level="1.8")
    assert not out.changed
    assert out.source == src
    assert "List.of(" in out.source
    assert "Arrays.asList(" not in out.source


def test_rewrites_list_of_in_initializer_for_java8():
    # docs/38: a plain `... = List.of(...)` local initializer is non-oracle code ->
    # still rewritten on Java 8.
    src = """package x;

import java.util.List;
import static org.junit.jupiter.api.Assertions.assertEquals;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() {
        List<String> expected = List.of("1", "2");
        assertEquals(expected, values());
    }
}
"""
    out = repair_compile_failure(src, java_source_level="1.8")
    assert out.changed
    assert "import java.util.Arrays;" in out.source
    assert "Arrays.asList(\"1\", \"2\")" in out.source
    assert "List.of(" not in out.source
    assert any(p.bucket == "java_source_level" for p in out.patches)


def test_keeps_list_of_in_fluent_assertion_chain():
    # docs/38 hardening: a chained/fluent oracle puts the expected value OUTSIDE the
    # first assert(...) paren span -- it is not a `= List.of` initializer, so it must
    # NOT be rewritten (the span-only guard would have missed this and edited oracle text).
    src = """package x;

import java.util.List;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { assertThat(values()).isEqualTo(List.of("1", "2")); }
}
"""
    out = repair_compile_failure(src, java_source_level="1.8")
    assert not out.changed
    assert out.source == src
    assert "Arrays.asList(" not in out.source


def test_keeps_list_of_in_non_assert_matcher():
    # The initializer-only rule is assertion-name independent: a non-`assert*` DSL
    # (here `then(...)`) holding an expected List.of is still left untouched.
    src = """package x;

import java.util.List;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { then(values()).isEqualTo(List.of("1", "2")); }
}
"""
    out = repair_compile_failure(src, java_source_level="1.8")
    assert not out.changed
    assert "Arrays.asList(" not in out.source


def test_moves_method_local_enum_to_test_class_scope():
    src = """package x;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() {
        enum Unmapped { CITY }
        use(Unmapped.CITY);
    }
}
"""
    out = repair_compile_failure(src)
    assert out.changed
    assert "        enum Unmapped" not in out.source
    assert "    private enum Unmapped { CITY }" in out.source
    assert "use(Unmapped.CITY);" in out.source


def test_no_change_for_unknown_compile_failure():
    src = "class T { void t() {} }\n"
    out = repair_compile_failure(src, compile_log="cannot find symbol Foo")
    assert not out.changed
    assert out.source == src


# --- docs/38 verifiable oracle-preservation invariant -----------------------------

def test_oracle_preserved_true_for_safe_repairs():
    # missing static import (insert-only) preserves the oracle skeleton.
    imp = """package x;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { assertSame("a", "a"); }
}
"""
    out = repair_compile_failure(imp)
    assert out.changed and out.oracle_preserved is True

    # initializer List.of rewrite (outside any assertion) preserves the oracle too.
    lst = """package x;

import java.util.List;
import static org.junit.jupiter.api.Assertions.assertEquals;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() {
        List<String> expected = List.of("1", "2");
        assertEquals(expected, values());
    }
}
"""
    out = repair_compile_failure(lst, java_source_level="1.8")
    assert out.changed and out.oracle_preserved is True


def test_oracle_signature_detects_assertion_argument_change():
    a = 'class T { void t(){ assertEquals(2, f()); } }'
    b = 'class T { void t(){ assertEquals(999, f()); } }'
    assert _oracle_signature(a) != _oracle_signature(b)
    # an inserted import / whitespace reflow does NOT change the signature
    c = 'import z;\nclass T { void t(){ assertEquals(2,   f()); } }'
    assert _oracle_signature(a) == _oracle_signature(c)


def test_repair_is_safe_reflects_oracle_preservation():
    assert repair_is_safe(CompileRepairResult(changed=False, source="x")) is True
    assert repair_is_safe(
        CompileRepairResult(changed=True, source="x", oracle_preserved=True)
    ) is True
    # a changed repair that did not preserve the oracle is NOT safe to persist.
    assert repair_is_safe(
        CompileRepairResult(changed=True, source="x", oracle_preserved=False)
    ) is False
