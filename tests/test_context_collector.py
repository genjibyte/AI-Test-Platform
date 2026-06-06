"""Context collection tests against the intact committed samples/calc fixture."""
from pathlib import Path

import pytest

from app.context.class_index import find_class_file, list_classes
from app.context.context_collector import (
    ContextError,
    _neighbor_source_excerpt,
    build_snapshot,
)
from app.context.maven_deps import summarize_build_constraints, summarize_dependencies
from app.targeting.target_selector import resolve_target

REPO = Path(__file__).resolve().parents[1] / "samples" / "calc"


def test_list_classes():
    refs = list_classes(REPO)
    fqns = {r.fqn for r in refs}
    assert "com.example.Calc" in fqns


def test_find_class_file():
    path = find_class_file(REPO, "com.example.Calc")
    assert path is not None and path.name == "Calc.java"


def test_resolve_target_ok():
    target, structure = resolve_target(REPO, "com.example.Calc", "max")
    assert target.exists
    assert target.method_exists is True
    assert structure is not None and structure.class_name == "Calc"


def test_resolve_target_missing_method():
    target, _ = resolve_target(REPO, "com.example.Calc", "nope")
    assert target.exists
    assert target.method_exists is False


def test_dependency_summary():
    deps = summarize_dependencies(REPO)
    arts = {(d.group_id, d.artifact_id, d.scope) for d in deps}
    assert ("org.junit.jupiter", "junit-jupiter", "test") in arts


def test_build_constraints_summary():
    constraints = summarize_build_constraints(REPO)
    assert constraints.java_source == "1.8"
    assert constraints.java_target == "1.8"


def test_build_snapshot_bounded_content():
    snap = build_snapshot(REPO, "com.example.Calc", "max")
    assert snap.target_class == "com.example.Calc"
    assert snap.target_method == "max"
    assert snap.target_method_source and "a > b" in snap.target_method_source
    # class structure present
    assert snap.class_structure.class_name == "Calc"
    # neighbor test discovered (CalcTest.java) with @Test methods
    assert snap.neighbor_test.found is True
    assert "max" in snap.neighbor_test.test_methods
    # maven deps summarized
    assert any(d.artifact_id == "junit-jupiter" for d in snap.maven_dependencies)
    assert snap.build_constraints.java_source == "1.8"


def test_neighbor_excerpt_skips_long_header_and_includes_test_body():
    source = (
        "/* " + ("license " * 180) + " */\n"
        "package com.example;\n"
        "import static org.junit.jupiter.api.Assertions.assertEquals;\n"
        "import org.junit.jupiter.api.Test;\n"
        "\n"
        "class CalcTest {\n"
        "  @Test\n"
        "  void max() {\n"
        "    assertEquals(2, new Calc().max(1, 2));\n"
        "  }\n"
        "}\n"
    )
    excerpt = _neighbor_source_excerpt(source, limit=300)
    assert len(excerpt) <= 300
    assert "import static org.junit.jupiter.api.Assertions.assertEquals;" in excerpt
    assert "@Test" in excerpt
    assert "assertEquals(2" in excerpt


def test_build_snapshot_missing_class_fails():
    with pytest.raises(ContextError):
        build_snapshot(REPO, "com.example.DoesNotExist")


def test_build_snapshot_missing_method_fails():
    with pytest.raises(ContextError):
        build_snapshot(REPO, "com.example.Calc", "ghost")
