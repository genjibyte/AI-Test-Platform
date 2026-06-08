"""Deterministic compile-only repair for generated Java tests.

Phase 3 starts small: repair only generated test source, only after a compile
failure, and only for low-risk buckets observed in Phase 2.5:

- missing JUnit static assertion imports;
- Java 8-incompatible ``List.of`` calls;
- method-local enum declarations.

Hardened after the docs/38 audit: static-import repair is **compile-log triggered**
(only adds an import javac actually flagged missing), and the ``List.of`` ->
``Arrays.asList`` rewrite is **confined to local-variable initializer position**
(``... = List.of(...)``) and additionally skips anything inside an assertion's
argument span. Oracle expected values are arguments *inside* a matcher call
(``assertEquals(List.of(...), x)``, ``assertThat(x).isEqualTo(List.of(...))``, or a
non-``assert*`` DSL), never a ``= List.of`` initializer, so the rewrite cannot reach
oracle text by construction -- independent of the assertion's name. No
oracle/test-failure repair happens here.

Beyond the by-construction guards, every result carries a verifiable
``oracle_preserved`` postcondition (the oracle skeleton -- assert.../fail(...) calls
-- is unchanged); ``repair_is_safe`` exposes it and the pipeline reverts any repair
that fails it.
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
    # Verifiable postcondition: the oracle skeleton (assert.../fail(...) calls) is
    # byte-identical (modulo whitespace) before and after repair. The pipeline
    # reverts a repair where this is False (defense-in-depth over the by-construction
    # guards). True when nothing changed.
    oracle_preserved: bool = True


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


_MISSING_SYMBOL_RE = re.compile(
    r"(?:符号|symbol)\s*[:：]\s*(?:方法|method|变量|variable|类|class)?\s*([A-Za-z_]\w*)"
)


def _missing_symbols_from_log(compile_log: str) -> set[str]:
    """Symbol names javac reported as not found ('找不到符号' / 'cannot find
    symbol', both locales)."""
    return {m.group(1) for m in _MISSING_SYMBOL_RE.finditer(compile_log or "")}


def _repair_junit_static_imports(
    source: str, compile_log: str = ""
) -> tuple[str, list[RepairPatch]]:
    patches: list[RepairPatch] = []
    flagged = _missing_symbols_from_log(compile_log)
    used = sorted(set(re.findall(r"\b(assert\w+|fail)\s*\(", source)))
    for name in used:
        if name not in _JUNIT_ASSERTIONS:
            continue
        # Log-triggered: when a compile log is available, only add the import the
        # compiler actually flagged missing (avoids spurious imports). With no log,
        # fall back to the source scan so non-pipeline callers keep working.
        if compile_log and name not in flagged:
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


def _matching_paren(source: str, open_idx: int) -> Optional[int]:
    """Index of the ')' that closes the '(' at open_idx, skipping string/char
    literals. Returns None if unbalanced."""
    depth = 0
    quote: Optional[str] = None
    escape = False
    for k in range(open_idx, len(source)):
        c = source[k]
        if quote:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == quote:
                quote = None
            continue
        if c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return k
    return None


def _assertion_arg_spans(source: str) -> list[tuple[int, int]]:
    """Char ranges covered by assert.../fail(...) calls, so a List.of inside an
    assertion's arguments (an oracle/expected-value expression) is never rewritten."""
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"\b(?:assert\w+|fail)\s*\(", source):
        close = _matching_paren(source, m.end() - 1)
        if close is not None:
            spans.append((m.start(), close))
    return spans


def _oracle_signature(source: str) -> tuple[str, ...]:
    """Ordered, whitespace-normalized text of every assert.../fail(...) call -- the
    test's oracle skeleton (which assertions exist + their expected-value arguments).
    A repair that leaves this tuple unchanged provably did not edit oracle text.
    Whitespace is normalized so a pure line-ending/import reflow is not flagged, while
    any change to an assertion's arguments is."""
    sig: list[str] = []
    for m in re.finditer(r"\b(?:assert\w+|fail)\s*\(", source):
        close = _matching_paren(source, m.end() - 1)
        if close is None:
            continue
        call = source[m.start() : close + 1]
        sig.append(re.sub(r"\s+", " ", call).strip())
    return tuple(sig)


def _is_initializer_position(source: str, idx: int) -> bool:
    """True when the token at ``idx`` is the right-hand side of an assignment /
    initializer -- the nearest preceding non-space char is a bare ``=`` (not ``==``,
    ``!=``, ``<=``, ``>=``, ``+=`` ...). This confines the List.of rewrite to
    ``... = List.of(...)`` local initializers. Oracle expected values appear as
    *arguments inside* a matcher call, never as a ``= List.of`` initializer, so
    restricting to this position keeps the rewrite off oracle text regardless of the
    assertion's name (assertEquals, assertThat-chains, or non-assert* DSLs)."""
    k = idx - 1
    while k >= 0 and source[k] in " \t\r\n":
        k -= 1
    if k < 0 or source[k] != "=":
        return False
    return k == 0 or source[k - 1] not in "=!<>+-*/%&|^~"


def _repair_java8_list_of(
    source: str, java_source_level: Optional[str]
) -> tuple[str, list[RepairPatch]]:
    if not _java8_or_older(java_source_level) or "List.of(" not in source:
        return source, []
    spans = _assertion_arg_spans(source)

    def _in_assertion(pos: int) -> bool:
        return any(s <= pos <= e for s, e in spans)

    out: list[str] = []
    i = 0
    changed = False
    needle = "List.of("
    while True:
        j = source.find(needle, i)
        if j == -1:
            out.append(source[i:])
            break
        out.append(source[i:j])
        # Rewrite only a plain ``= List.of(...)`` local initializer that is not
        # inside an assertion span; anything else (matcher arguments, returns, call
        # arguments) is left as-is -> stays a compile error for human review rather
        # than risk editing oracle text.
        if _is_initializer_position(source, j) and not _in_assertion(j):
            out.append("Arrays.asList(")
            changed = True
        else:
            out.append(needle)
        i = j + len(needle)
    if not changed:
        return source, []
    fixed = _insert_import("".join(out), "import java.util.Arrays;")
    return fixed, [
        RepairPatch(
            bucket="java_source_level",
            description="replace Java 9 List.of with Java 8 Arrays.asList (initializer position only)",
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

    repaired, ps = _repair_junit_static_imports(repaired, compile_log)
    patches.extend(ps)
    repaired, ps = _repair_java8_list_of(repaired, java_source_level)
    patches.extend(ps)
    repaired, ps = _repair_method_local_enums(repaired)
    patches.extend(ps)

    return CompileRepairResult(
        changed=repaired != source,
        source=repaired,
        patches=patches,
        oracle_preserved=_oracle_signature(source) == _oracle_signature(repaired),
    )


def repair_is_safe(result: CompileRepairResult) -> bool:
    """A repair is safe to persist iff it changed nothing or preserved the oracle
    skeleton. The generate pipeline reverts (does not write / re-run Maven for) a
    repair that fails this check."""
    return (not result.changed) or result.oracle_preserved
