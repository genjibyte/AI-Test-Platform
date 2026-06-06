"""Deterministic quality gate for generated Java unit tests.

The gate is deliberately conservative: it only inspects facts and generated
test source. It never calls an LLM and never edits the generated test.
"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    code: str
    severity: str
    message: str
    evidence: Optional[str] = None


class QualityGateResult(BaseModel):
    checked: bool = True
    status: str
    blocking_issues: list[QualityIssue] = Field(default_factory=list)
    warnings: list[QualityIssue] = Field(default_factory=list)
    # Informational notes from the model's own self-report (e.g. declared risks).
    # Surfaced for the human reviewer but do NOT affect status: an honest model
    # disclosing a risk must not be penalised below a silent one.
    advisories: list[QualityIssue] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


_WEAK_ASSERTIONS = {"assertNotNull", "assertNull", "fail"}
_ASSERTION_RE = re.compile(
    r"\b(?:Assertions\.)?(assert[A-Z]\w*|fail)\s*\(|\bassertThat\s*\("
)
# Count JUnit5 test methods. Plain @Test plus the other JUnit5 test kinds, so a
# valid parameterized/repeated/factory test is not falsely flagged "no @Test".
_TEST_RE = re.compile(
    r"@\s*(?:Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b"
)
_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')

_UNSTABLE_PATTERNS = (
    ("thread_sleep", re.compile(r"\bThread\.sleep\s*\("), "uses Thread.sleep"),
    ("randomness", re.compile(r"\b(?:new\s+Random|Math\.random)\s*\("), "uses randomness"),
    (
        "wall_clock_time",
        re.compile(r"\b(?:System\.(?:currentTimeMillis|nanoTime)|Instant\.now|LocalDate\.now|LocalDateTime\.now)\s*\("),
        "uses wall-clock time",
    ),
    (
        "environment_dependency",
        re.compile(r"\bSystem\.(?:getenv|getProperty)\s*\("),
        "reads process environment or system properties",
    ),
    (
        "external_io",
        re.compile(r"\b(?:new\s+File|Paths\.get|Files\.|URL|URI|Socket|HttpClient)\b"),
        "uses file, network, or external I/O APIs",
    ),
)

_INTERNAL_ACCESS_RE = re.compile(
    r"\b(?:getDeclaredField|getDeclaredMethod|getDeclaredConstructor|setAccessible)\s*\("
)


def _strip_java_comments(text: str) -> str:
    """Remove Java line/block comments while preserving strings and newlines."""
    out: list[str] = []
    i = 0
    quote: Optional[str] = None
    escape = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if quote:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i < len(text) - 1:
                if text[i] == "*" and text[i + 1] == "/":
                    i += 2
                    break
                out.append("\n" if text[i] in "\r\n" else " ")
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_strings(text: str) -> str:
    return _STRING_RE.sub('""', text)


def _assertion_names(source: str) -> list[str]:
    names: list[str] = []
    for match in _ASSERTION_RE.finditer(source):
        if match.group(1):
            names.append(match.group(1))
        else:
            names.append("assertThat")
    return names


def _find_call_args(source: str, call_name: str) -> list[list[str]]:
    calls: list[list[str]] = []
    for match in re.finditer(rf"\b(?:Assertions\.)?{re.escape(call_name)}\s*\(", source):
        start = match.end()
        depth = 1
        quote: Optional[str] = None
        escape = False
        args_start = start
        for i in range(start, len(source)):
            ch = source[i]
            if quote:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote:
                    quote = None
                continue
            if ch in {"'", '"'}:
                quote = ch
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    calls.append(_split_args(source[args_start:i]))
                    break
    return calls


def _split_args(text: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    quote: Optional[str] = None
    escape = False
    for i, ch in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if ch in {"'", '"'}:
            quote = ch
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            args.append(text[start:i].strip())
            start = i + 1
    tail = text[start:].strip()
    if tail:
        args.append(tail)
    return args


def _norm_expr(expr: str) -> str:
    expr = re.sub(r"\s+", "", expr)
    expr = re.sub(r"^\((.*)\)$", r"\1", expr)
    return expr


def _tautological_evidence(source: str) -> list[str]:
    evidence: list[str] = []
    for name in ("assertEquals", "assertSame", "assertArrayEquals", "assertIterableEquals"):
        for args in _find_call_args(source, name):
            if len(args) >= 2 and _norm_expr(args[0]) == _norm_expr(args[1]):
                evidence.append(f"{name}({args[0]}, {args[1]})")
    for args in _find_call_args(source, "assertTrue"):
        if args and _norm_expr(args[0]).lower() == "true":
            evidence.append("assertTrue(true)")
    for args in _find_call_args(source, "assertFalse"):
        if args and _norm_expr(args[0]).lower() == "false":
            evidence.append("assertFalse(false)")
    return evidence


def _add(
    issues: list[QualityIssue],
    code: str,
    severity: str,
    message: str,
    evidence: Optional[str] = None,
) -> None:
    issues.append(
        QualityIssue(code=code, severity=severity, message=message, evidence=evidence)
    )


def evaluate_test_quality(
    source: str,
    *,
    execution: Optional[dict] = None,
    coverage_delta: Optional[dict] = None,
    production_code_touched: bool = False,
    target_class: Optional[str] = None,
    target_method: Optional[str] = None,
    grounding: Optional[dict] = None,
) -> QualityGateResult:
    """Evaluate generated-test quality without changing code or verdicts."""
    source = source or ""
    execution = execution or {}
    coverage_delta = coverage_delta or {}
    grounding = grounding or {}
    code = _strip_java_comments(source)
    stripped = _strip_strings(code)
    assertions = _assertion_names(stripped)
    weak = [a for a in assertions if a in _WEAK_ASSERTIONS]
    tautologies = _tautological_evidence(code)
    test_methods = len(_TEST_RE.findall(stripped))

    blocking: list[QualityIssue] = []
    warnings: list[QualityIssue] = []
    advisories: list[QualityIssue] = []

    outcome = execution.get("gen_outcome")
    if outcome and outcome not in {"PASS", "TEST_FAILURE"}:
        _add(blocking, "not_executed", "blocker", "generated test did not execute", outcome)
    elif outcome == "TEST_FAILURE":
        _add(warnings, "test_failure", "warning", "generated test executed but failed", outcome)

    if production_code_touched:
        _add(blocking, "production_code_touched", "blocker", "generated patch touched production code")

    if coverage_delta.get("coverage_dropped") is True:
        _add(blocking, "coverage_dropped", "blocker", "generated test lowered coverage")

    if test_methods == 0:
        _add(blocking, "no_test_methods", "blocker", "no @Test methods were found")

    if not assertions:
        _add(blocking, "no_assertions", "blocker", "no assertions were found")
    elif len(weak) == len(assertions):
        _add(blocking, "only_weak_assertions", "blocker", "all assertions are weak", ", ".join(assertions))
    elif weak and len(weak) / len(assertions) >= 0.75:
        _add(warnings, "weak_assertion_heavy", "warning", "most assertions are weak", ", ".join(weak))

    if tautologies:
        _add(
            blocking,
            "tautological_assertion",
            "blocker",
            "assertion compares a value with itself or a literal truth",
            "; ".join(tautologies[:3]),
        )

    for code, pattern, message in _UNSTABLE_PATTERNS:
        if pattern.search(stripped):
            _add(blocking, code, "blocker", message)

    if _INTERNAL_ACCESS_RE.search(stripped):
        _add(blocking, "internal_implementation_access", "blocker", "uses reflection to inspect internals")

    simple_target = target_class.rsplit(".", 1)[-1] if target_class else None
    if simple_target and simple_target not in stripped and not (target_method and target_method in stripped):
        _add(
            warnings,
            "no_obvious_target_reference",
            "warning",
            "generated test does not obviously reference the target class or method",
            target_class,
        )

    risk_flags = [
        r for r in grounding.get("risk_flags", [])
        if str(r).strip() and str(r).strip().lower() not in {"none", "no risk", "n/a"}
    ]
    if risk_flags:
        _add(advisories, "model_declared_risk", "advisory", "model declared generation risks", "; ".join(risk_flags))

    if assertions and not grounding.get("behavior_sources"):
        _add(
            warnings,
            "missing_behavior_sources",
            "warning",
            "model did not provide behavior_sources for oracle review",
        )

    status = "FAIL" if blocking else ("REVIEW" if warnings else "PASS")
    metrics = {
        "test_methods": test_methods,
        "assertions": len(assertions),
        "weak_assertions": len(weak),
        "tautological_assertions": len(tautologies),
    }
    return QualityGateResult(
        checked=True,
        status=status,
        blocking_issues=blocking,
        warnings=warnings,
        advisories=advisories,
        metrics=metrics,
    )
