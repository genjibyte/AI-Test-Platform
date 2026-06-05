"""Tests for the independent test-file writer + boundary guards (P2-T06).

Pure-string normalization is tested directly. File-writing tests check path,
creation, and the no-clobber / no-prod-touch guards WITHOUT reading back file
content (so they are robust regardless of host file behavior).
"""
import pytest

from app.generate.test_writer import (
    TestWriteError,
    normalize_test_source,
    write_generated_test,
)
from app.llm.schema import TestGenerationResult


def _result(**kw) -> TestGenerationResult:
    base = dict(
        target_class="com.example.Calc",
        target_method="max",
        package="com.example",
        test_class_name="CalcAiGeneratedTest",
        file_name="CalcAiGeneratedTest.java",
        imports=["org.junit.jupiter.api.Test"],
        test_source="package com.example;\n\nclass CalcTest {\n  void a() {}\n}\n",
    )
    base.update(kw)
    return TestGenerationResult(**base)


def test_normalize_renames_colliding_class():
    out = normalize_test_source(
        "package com.example;\n\nclass CalcTest { void a() {} }",
        "com.example",
        "CalcAiGeneratedTest",
    )
    assert "class CalcAiGeneratedTest" in out
    assert "class CalcTest" not in out
    assert out.count("package com.example;") == 1


def test_normalize_injects_missing_package():
    out = normalize_test_source("class FooTest {}", "com.x", "FooAiGeneratedTest")
    assert out.startswith("package com.x;")
    assert "class FooAiGeneratedTest" in out


def _make_repo(tmp_path):
    main = tmp_path / "src/main/java/com/example"
    main.mkdir(parents=True)
    (main / "Calc.java").write_text("package com.example; class Calc {}", "utf-8")
    return tmp_path


def test_writes_under_test_root(tmp_path):
    repo = _make_repo(tmp_path)
    res = write_generated_test(repo, _result())
    assert res.created
    assert res.file_path == "src/test/java/com/example/CalcAiGeneratedTest.java"
    assert (repo / res.file_path).exists()
    assert res.production_code_touched is False


def test_refuses_overwrite(tmp_path):
    repo = _make_repo(tmp_path)
    write_generated_test(repo, _result())
    with pytest.raises(TestWriteError):
        write_generated_test(repo, _result())  # second time -> exists -> refuse


def test_does_not_touch_main_sources(tmp_path):
    repo = _make_repo(tmp_path)
    before = {p.relative_to(repo) for p in (repo / "src/main").rglob("*")}
    write_generated_test(repo, _result())
    after = {p.relative_to(repo) for p in (repo / "src/main").rglob("*")}
    assert before == after  # no main-source files added/removed/renamed
