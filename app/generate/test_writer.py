"""Independent test-file writer with boundary guards (P2-T06).

Writes the generated test as a NEW ``<Target>AiGeneratedTest.java`` under the
module's ``src/test/java``. Hard guards (docs/07 P2/P5):

- normalizes the top-level class name to the deterministic test class name so it
  can never collide with an existing test (e.g. the model reusing ``CalcTest``);
- writes ONLY under ``src/test/java`` — never ``src/main``;
- refuses to overwrite an existing file (no clobbering existing tests);
- never modifies production code or existing tests.

This module performs NO generation and NO execution.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel

from app.context.class_index import find_class_file, find_source_roots
from app.llm.schema import TestGenerationResult


class TestWriteError(Exception):
    """Raised when writing would violate a boundary guard."""

    __test__ = False  # not a pytest test class despite the 'Test' prefix


class WriteResult(BaseModel):
    file_path: str                       # relative to repo root
    test_class_name: str
    created: bool
    production_code_touched: bool = False
    content: str                         # normalized content (patch preview)


def normalize_test_source(
    source: str, package: Optional[str], test_class_name: str
) -> str:
    """Force the package and rename the first top-level class to the target name."""
    # drop any existing package declaration(s)
    body = re.sub(r"(?m)^\s*package\s+[\w.]+\s*;\s*\n?", "", source).lstrip("\n")
    # rename first `class X` -> the deterministic test class name
    body = re.sub(
        r"(\bclass\s+)(\w+)", lambda m: m.group(1) + test_class_name, body, count=1
    )
    if package:
        return f"package {package};\n\n{body}".rstrip() + "\n"
    return body.rstrip() + "\n"


def _module_test_root(repo_dir: Path, target_class: str) -> Path:
    """Test source root in the same module as the target class."""
    main_file = find_class_file(repo_dir, target_class)
    if main_file is not None:
        # .../<module>/src/main/java/<pkg>/<Class>.java -> <module>/src/test/java
        p = main_file
        while p.parent != p:
            if p.name == "java" and p.parent.name == "main" and p.parent.parent.name == "src":
                return p.parent.parent / "test" / "java"
            p = p.parent
    test_roots = find_source_roots(repo_dir, "test")
    if test_roots:
        return test_roots[0]
    return repo_dir / "src" / "test" / "java"


def write_generated_test(
    repo_dir: Union[str, Path],
    result: TestGenerationResult,
    overwrite: bool = False,
) -> WriteResult:
    repo_dir = Path(repo_dir)
    test_root = _module_test_root(repo_dir, result.target_class)
    pkg_path = (result.package or "").replace(".", "/")
    target_dir = test_root / pkg_path if pkg_path else test_root
    target_file = target_dir / result.file_name

    # guard: must stay under a src/test/java root
    if "test" not in target_file.parts or "src" not in target_file.parts:
        raise TestWriteError(f"refusing to write outside src/test/java: {target_file}")

    if target_file.exists() and not overwrite:
        raise TestWriteError(f"refusing to overwrite existing file: {target_file}")

    content = normalize_test_source(
        result.test_source, result.package, result.test_class_name
    )

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")

    return WriteResult(
        file_path=str(target_file.relative_to(repo_dir)).replace("\\", "/"),
        test_class_name=result.test_class_name,
        created=True,
        production_code_touched=False,
        content=content,
    )
