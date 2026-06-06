"""Pure-text Java parser tests (P2-T01). No file I/O -> immune to host quirks."""
from app.context.java_parser import extract_test_methods, parse_java

SOURCE = """package com.example.demo;

import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.assertEquals;

/** A demo service. */
public class OrderService {
    private final Repo repo;        // dependency
    private int counter = 0;
    public static final String TAG = "x; not a field end";

    public OrderService(Repo repo) {
        this.repo = repo;
    }

    /**
     * Totals item values.
     *
     * @return the sum of all item values
     * @throws IllegalStateException when the {@code repo} is closed
     */
    public int total(List<Integer> items) throws IllegalStateException {
        if (items == null) {
            throw new NullPointerException("items");
        }
        int s = 0;
        for (int i : items) { s += i; }
        return s;
    }

    protected Map<String, Integer> index() { return null; }

    private void secret() { counter++; }
}
"""


def test_package_and_imports():
    s = parse_java(SOURCE)
    assert s.package == "com.example.demo"
    assert "java.util.List" in s.imports
    assert "static org.junit.jupiter.api.Assertions.assertEquals" in s.imports


def test_class_name_and_kind():
    s = parse_java(SOURCE)
    assert s.class_name == "OrderService"
    assert s.kind == "class"


def test_fields():
    s = parse_java(SOURCE)
    names = {f.name: f for f in s.fields}
    assert "repo" in names and names["repo"].type == "Repo"
    assert "counter" in names
    assert "TAG" in names  # string literal with ';' inside must not break parsing


def test_constructor():
    s = parse_java(SOURCE)
    assert len(s.constructors) == 1
    ctor = s.constructors[0]
    assert ctor.name == "OrderService"
    assert ctor.params[0].type == "Repo" and ctor.params[0].name == "repo"


def test_only_public_protected_methods():
    s = parse_java(SOURCE)
    names = {m.name for m in s.methods}
    assert names == {"total", "index"}        # private 'secret' excluded
    total = next(m for m in s.methods if m.name == "total")
    assert total.return_type == "int"
    assert total.throws == ["IllegalStateException"]
    assert total.javadoc_return == "the sum of all item values"
    assert total.javadoc_throws == [
        "IllegalStateException when the {@code repo} is closed"
    ]
    assert total.body_throws == ["NullPointerException"]
    assert total.params[0].name == "items"
    assert "return s;" in total.source


NESTED_SOURCE = """package com.example;

public final class Option {
    private final String opt;
    private Option(Builder b) { this.opt = b.opt; }
    public String getOpt() { return opt; }
    public static Builder builder(String opt) { return new Builder(opt); }

    public static final class Builder {
        private String opt;
        Builder(String opt) { this.opt = opt; }
        public Builder longOpt(String l) { return this; }
        public Option build() { return new Option(this); }
    }

    public enum Kind { A, B }
}
"""


def test_nested_classes_extracted_not_fields():
    s = parse_java(NESTED_SOURCE)
    assert s.class_name == "Option"
    # nested types are captured by simple name...
    assert "Builder" in s.nested_classes
    assert "Kind" in s.nested_classes
    # ...and NOT misclassified as fields of type "class"/"enum"
    field_names = {f.name for f in s.fields}
    assert "Builder" not in field_names
    assert "Kind" not in field_names
    # nested members are not hoisted into the owner's public methods
    assert {m.name for m in s.methods} == {"getOpt", "builder"}


def test_extract_test_methods():
    src = """package x;
    import org.junit.jupiter.api.Test;
    class FooTest {
        @Test void alpha() {}
        @Test
        void beta() {}
        void notATest() {}
    }
    """
    assert extract_test_methods(src) == ["alpha", "beta"]
