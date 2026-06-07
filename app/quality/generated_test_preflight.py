"""Deterministic preflight checks for generated Java tests.

The preflight is intentionally narrow. It validates class-qualified calls to the
target class against the bounded context method list before Maven runs. It never
edits generated tests and never tries to infer receiver variable types.
"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field

from app.models.context_snapshot import ContextSnapshot
from app.models.java_source import JavaMethod


class PreflightIssue(BaseModel):
    code: str
    severity: str
    message: str
    evidence: Optional[str] = None


class GeneratedTestPreflightResult(BaseModel):
    checked: bool = True
    status: str
    blocking_issues: list[PreflightIssue] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class _Call(BaseModel):
    owner: str
    method: str
    arity: int
    evidence: str
    args: list[str] = Field(default_factory=list)


def _strip_java_comments(source: str) -> str:
    out: list[str] = []
    i = 0
    quote: Optional[str] = None
    escape = False
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
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
            while i < len(source) and source[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i < len(source) - 1:
                if source[i] == "*" and source[i + 1] == "/":
                    i += 2
                    break
                out.append("\n" if source[i] in "\r\n" else " ")
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _mask_string_literals(source: str) -> str:
    out: list[str] = []
    i = 0
    quote: Optional[str] = None
    escape = False
    while i < len(source):
        ch = source[i]
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                out.append(quote)
                quote = None
            elif ch in "\r\n":
                out.append(ch)
            else:
                out.append(" ")
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


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
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            args.append(text[start:i].strip())
            start = i + 1
    tail = text[start:].strip()
    if tail:
        args.append(tail)
    return args


def _find_matching_close(source: str, open_idx: int) -> Optional[int]:
    depth = 1
    quote: Optional[str] = None
    escape = False
    for i in range(open_idx + 1, len(source)):
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
                return i
    return None


def _target_owners(context: ContextSnapshot) -> set[str]:
    simple = context.target_class.rsplit(".", 1)[-1]
    return {simple, context.target_class}


def _target_calls(source: str, context: ContextSnapshot) -> list[_Call]:
    code = _mask_string_literals(_strip_java_comments(source))
    owners = sorted(_target_owners(context), key=len, reverse=True)
    owner_re = "|".join(re.escape(o) for o in owners)
    pattern = re.compile(
        rf"(?<![\w$])(?P<owner>{owner_re})\s*\.\s*(?P<method>[A-Za-z_$][\w$]*)\s*\("
    )
    calls: list[_Call] = []
    for match in pattern.finditer(code):
        open_idx = match.end() - 1
        close_idx = _find_matching_close(code, open_idx)
        if close_idx is None:
            continue
        args = _split_args(code[open_idx + 1:close_idx])
        evidence = " ".join(code[match.start(): close_idx + 1].split())
        calls.append(
            _Call(
                owner=match.group("owner"),
                method=match.group("method"),
                arity=len(args),
                evidence=evidence[:240],
                args=args,
            )
        )
    return calls


def _is_varargs(method: JavaMethod) -> bool:
    return bool(method.params and method.params[-1].type.strip().endswith("..."))


def _method_index(methods: list[JavaMethod]) -> dict[str, list[JavaMethod]]:
    index: dict[str, list[JavaMethod]] = {}
    for method in methods:
        index.setdefault(method.name, []).append(method)
    return index


def _arity_matches(call: _Call, overloads: list[JavaMethod]) -> bool:
    for method in overloads:
        arity = len(method.params)
        if _is_varargs(method):
            fixed = arity - 1
            if call.arity >= fixed:
                return True
        elif call.arity == arity:
            return True
    return False


def _has_ambiguous_varargs_pair(overloads: list[JavaMethod]) -> bool:
    varargs = [m for m in overloads if _is_varargs(m)]
    if len(varargs) < 2:
        return False
    tails = {m.params[-1].type.strip() for m in varargs}
    return any(t.endswith("boolean...") for t in tails) and any(
        t.endswith("Boolean...") for t in tails
    )


def _fixed_arity_match(call: _Call, overloads: list[JavaMethod]) -> bool:
    """A non-varargs overload exactly matches the call arity. Java binds a
    fixed-arity overload before a varargs one (JLS 15.12.2), so a primitive/boxed
    varargs pair is NOT ambiguous for a call that a fixed overload accepts."""
    return any(
        not _is_varargs(m) and len(m.params) == call.arity for m in overloads
    )


# --- Overload-ambiguity detection (docs/36). Lexical only, never type inference;
# any UNKNOWN argument makes the call defer to Maven (conservative, FP-averse). ---
_PRIMITIVE_TYPES = {"boolean", "byte", "char", "short", "int", "long", "float", "double"}
_PRIMITIVE_LIT_RE = re.compile(
    r"^(?:true|false|'(?:\\.|[^'])+'"          # boolean / char literal
    r"|[+-]?(?:0[xX][0-9a-fA-F_]+|\d[\d_]*)[lL]?"   # int / long / hex
    r"|[+-]?(?:\d[\d_]*\.\d*|\.\d+|\d[\d_]*)(?:[eE][+-]?\d+)?[fFdD]?)$"  # float/double
)
_BOXED_LIT_RE = re.compile(
    r"^(?:(?:Boolean|Integer|Long|Double|Float|Short|Byte|Character)\s*\.\s*"
    r"(?:TRUE|FALSE|valueOf\s*\(.*\))"
    r"|new\s+(?:Boolean|Integer|Long|Double|Float|Short|Byte|Character)\s*\(.*\))$"
)


def _classify_arg(arg: str) -> str:
    a = arg.strip()
    if a == "null":
        return "NULL"
    if _BOXED_LIT_RE.match(a):
        return "BOXED"
    if _PRIMITIVE_LIT_RE.match(a):
        return "PRIMITIVE"
    return "UNKNOWN"


def _param_is_reference(jtype: str) -> bool:
    return jtype.strip().rstrip(".") not in _PRIMITIVE_TYPES


def _scalar_same_arity(call: _Call, overloads: list[JavaMethod]) -> list[JavaMethod]:
    return [m for m in overloads if not _is_varargs(m) and len(m.params) == call.arity]


_WRAPPER = {
    "int": "Integer", "boolean": "Boolean", "long": "Long", "double": "Double",
    "float": "Float", "short": "Short", "byte": "Byte", "char": "Character",
}


def _null_overload_ambiguous(call: _Call, overloads: list[JavaMethod]) -> bool:
    """Shape A: a bare null is ambiguous ONLY when >=2 same-arity overloads are
    identical at every other position and differ only by the reference type at
    the null position, AND the call's other args confirmedly match those shared
    *primitive* positions (so nothing else disambiguates). Anything less certain
    -- a reference other-position, or an UNKNOWN/non-primitive other arg -- means
    another arg may pick the overload, so we DEFER to Maven (never over-reject).

    e.g. FLAG  toBoolean(null)            : toBoolean(Boolean) vs toBoolean(String)
         FLAG  toDouble(null, 0.0)        : toDouble(String,double) vs toDouble(BigDecimal,double)
         DEFER f(null, 1)                 : f(String,int) vs f(Integer,String) -- the `1` picks f(String,int)
    """
    same = _scalar_same_arity(call, overloads)
    if len(same) < 2:
        return False
    for p, arg in enumerate(call.args):
        if _classify_arg(arg) != "NULL":
            continue
        others_idx = [j for j in range(call.arity) if j != p]
        # group reference-at-p overloads by their identical signature elsewhere
        groups: dict[tuple, set] = {}
        for ov in same:
            if not _param_is_reference(ov.params[p].type):
                continue  # this overload can't take null at p
            sig = tuple(ov.params[j].type.strip() for j in others_idx)
            groups.setdefault(sig, set()).add(ov.params[p].type.strip())
        for sig, ref_types in groups.items():
            if len(ref_types) < 2:
                continue
            # every other position must be a primitive the call's arg confirmedly
            # fits; else another arg could disambiguate -> defer.
            if all(
                t.rstrip(".") in _PRIMITIVE_TYPES
                and _classify_arg(call.args[j]) in ("PRIMITIVE", "BOXED")
                for t, j in zip(sig, others_idx)
            ):
                return True
    return False


def _boxed_primitive_mix_ambiguous(call: _Call, overloads: list[JavaMethod]) -> bool:
    """Shape B: mixing a boxed and a primitive arg is ambiguous ONLY when the
    same-arity family contains an all-primitive overload AND its EXACT wrapper
    counterpart (e.g. f(int,int) and f(Integer,Integer)). A reference overload
    that is not the wrapper family (e.g. f(String,String)) does not make the call
    ambiguous, so it must not be flagged. Any UNKNOWN/NULL arg defers to Maven.

    e.g. FLAG  toBoolean(Integer.valueOf(3), 1, 2) with int.. / Integer.. family
         DEFER f(Integer.valueOf(1), 2)  with f(int,int) / f(String,String) -- binds f(int,int)
    """
    kinds = [_classify_arg(a) for a in call.args]
    if "BOXED" not in kinds or "PRIMITIVE" not in kinds:
        return False
    if any(k in ("UNKNOWN", "NULL") for k in kinds):
        return False
    same = _scalar_same_arity(call, overloads)
    sigs = {tuple(p.type.strip() for p in ov.params) for ov in same}
    for ov in same:
        if not ov.params or not all(not _param_is_reference(p.type) for p in ov.params):
            continue  # not an all-primitive overload
        wrapper_sig = tuple(_WRAPPER.get(p.type.strip()) for p in ov.params)
        if None not in wrapper_sig and wrapper_sig in sigs:
            return True  # found f(int..) and its exact f(Integer..) counterpart
    return False


def evaluate_generated_test_preflight(
    source: str,
    context: ContextSnapshot,
) -> GeneratedTestPreflightResult:
    """Validate target-class calls against the rendered method list."""
    methods = _method_index(context.class_structure.methods)
    calls = _target_calls(source or "", context)
    blocking: list[PreflightIssue] = []

    for call in calls:
        overloads = methods.get(call.method)
        if not overloads:
            blocking.append(
                PreflightIssue(
                    code="unlisted_target_method",
                    severity="blocker",
                    message="target-class call is not in the rendered method list",
                    evidence=call.evidence,
                )
            )
            continue
        if not _arity_matches(call, overloads):
            allowed = sorted({len(m.params) for m in overloads})
            blocking.append(
                PreflightIssue(
                    code="unlisted_target_overload_arity",
                    severity="blocker",
                    message="target-class call arity is not in the rendered method list",
                    evidence=f"{call.evidence} arity={call.arity} allowed={allowed}",
                )
            )
            continue
        if (
            _has_ambiguous_varargs_pair(overloads)
            and call.arity > 1
            and not _fixed_arity_match(call, overloads)
        ):
            blocking.append(
                PreflightIssue(
                    code="ambiguous_varargs_overload_call",
                    severity="blocker",
                    message="primitive/boxed varargs overload pair must be called with one typed array",
                    evidence=call.evidence,
                )
            )
            continue
        if _null_overload_ambiguous(call, overloads):
            blocking.append(
                PreflightIssue(
                    code="ambiguous_null_overload_call",
                    severity="blocker",
                    message="bare null is ambiguous between same-arity reference-type overloads",
                    evidence=call.evidence,
                )
            )
            continue
        if _boxed_primitive_mix_ambiguous(call, overloads):
            blocking.append(
                PreflightIssue(
                    code="ambiguous_boxed_primitive_overload_call",
                    severity="blocker",
                    message="mixed boxed/primitive args are ambiguous in a primitive/boxed overload family",
                    evidence=call.evidence,
                )
            )
            continue

    return GeneratedTestPreflightResult(
        checked=True,
        status="FAIL" if blocking else "PASS",
        blocking_issues=blocking,
        metrics={"target_class_calls": len(calls)},
    )
