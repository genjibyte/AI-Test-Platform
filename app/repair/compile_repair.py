"""Deterministic compile-only repair for generated Java tests.

Phase 3 starts small: repair only generated test source, only after a compile
failure, and only for low-risk buckets observed in Phase 2.5:

- missing JUnit static assertion imports;
- Java 8-incompatible ``List.of`` calls;
- method-local enum declarations.

No oracle/test-failure repair happens here.
"""
from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field


class RepairPatch(BaseModel):
    bucket: str
    description: str


class CompileRepairResult(BaseModel):
    changed: bool
    source: str
    patches: List[RepairPatch] = Field(default_factory=list)


_JUNIT_ASSERTIONS = {
    "assertAll",
    "assertArrayEquals",
    "assertDoesNotThrow",
    "assertEquals",
    "assertFalse",
    "assertInstanceOf",
    "assertIterableEquals",
    "assertLinesMatch",
    "assertNotEquals",
    "assertNotNull",
    "assertNotSame",
    "assertNull",
    "assertSame",
    "assertThrows",
    "assertTimeout",
    "assertTimeoutPreemptively",
    "assertTrue",
    "fail",
}


def _java8_or_older(java_source_level: Optional[str]) -> bool:
    if not java_source_level:
        return False
    value = java_source_level.strip().lower()
    if value.startswith("1."):
        value = value[2:]
    try:
        return int(value) <= 8
    except ValueError:
        return False


def _insert_import(source: str, import_line: str) -> str:
    if import_line in source:
        return source
    lines = source.splitlines()
    insert_at = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("package ") or stripped.startswith("import "):
            insert_at = idx + 1
    lines.insert(insert_at, import_line)
    return "\n".join(lines) + ("\n" if source.endswith("\n") else "")


def _repair_junit_static_imports(source: str) -> tuple[str, list[RepairPatch]]:
    patches: list[RepairPatch] = []
    used = sorted(set(re.findall(r"\b(assert\w+|fail)\s*\(", source)))
    for name in used:
        if name not in _JUNIT_ASSERTIONS:
            continue
        import_line = f"import static org.junit.jupiter.api.Assertions.{name};"
        if import_line not in source:
            source = _insert_import(source, import_line)
            patches.append(
                RepairPatch(
                    bucket="missing_static_import",
                    description=f"add static import for {name}",
                )
            )
    return source, patches


def _repair_java8_list_of(
    source: str, java_source_level: Optional[str]
) -> tuple[str, list[RepairPatch]]:
    if not _java8_or_older(java_source_level) or "List.of(" not in source:
        return source, []
    fixed = source.replace("List.of(", "Arrays.asList(")
    fixed = _insert_import(fixed, "import java.util.Arrays;")
    return fixed, [
        RepairPatch(
            bucket="java_source_level",
            description="replace Java 9 List.of with Java 8 Arrays.asList",
        )
    ]


def _repair_method_local_enums(source: str) -> tuple[str, list[RepairPatch]]:
    lines = source.splitlines()
    moved: list[str] = []
    out: list[str] = []
    depth = 0
    for line in lines:
        match = re.match(r"^(\s*)enum\s+(\w+)\s*\{([^}]*)\}\s*$", line)
        if match and depth >= 2:
            moved.append(f"    private enum {match.group(2)} {{{match.group(3)}}}")
            depth += line.count("{") - line.count("}")
            continue
        out.append(line)
        depth += line.count("{") - line.count("}")

    if not moved:
        return source, []

    # Insert helper enums before the final top-level class brace.
    insert_at = len(out)
    for idx in range(len(out) - 1, -1, -1):
        if out[idx].strip() == "}":
            insert_at = idx
            break
    repaired = out[:insert_at] + [""] + moved + out[insert_at:]
    return "\n".join(repaired) + ("\n" if source.endswith("\n") else ""), [
        RepairPatch(
            bucket="method_local_type",
            description="move method-local enum to test class scope",
        )
    ]


def repair_compile_failure(
    source: str,
    compile_log: str = "",
    java_source_level: Optional[str] = None,
) -> CompileRepairResult:
    """Apply deterministic compile-failure repairs to a generated test source."""
    patches: list[RepairPatch] = []
    repaired = source

    repaired, ps = _repair_junit_static_imports(repaired)
    patches.extend(ps)
    repaired, ps = _repair_java8_list_of(repaired, java_source_level)
    patches.extend(ps)
    repaired, ps = _repair_method_local_enums(repaired)
    patches.extend(ps)

    return CompileRepairResult(
        changed=repaired != source,
        source=repaired,
        patches=patches,
    )
