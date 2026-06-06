from app.repair.compile_repair import repair_compile_failure


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


def test_rewrites_list_of_for_java8():
    src = """package x;

import java.util.List;

class TAiGeneratedTest {
    @org.junit.jupiter.api.Test
    void t() { assertEquals(List.of("1", "2"), values()); }
}
"""
    out = repair_compile_failure(src, java_source_level="1.8")
    assert out.changed
    assert "import java.util.Arrays;" in out.source
    assert "Arrays.asList(\"1\", \"2\")" in out.source
    assert "List.of(" not in out.source


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
