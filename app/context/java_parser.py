"""Heuristic Java source parser (P2-T01).

A pragmatic, dependency-free parser that extracts the structural facts Phase 2
needs: package, imports, primary type, fields, constructors, and
public/protected methods (with full method source for the chosen target).

It is intentionally lightweight (not a full Java grammar). It masks comments and
string/char literals so braces/semicolons inside them never confuse the scanner,
then walks the primary type body brace-by-brace. ``parse_java`` is a PURE
function over text — easy to unit-test and immune to any filesystem quirks.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.models.java_source import (
    JavaClassStructure,
    JavaConstructor,
    JavaField,
    JavaMethod,
    JavaParam,
)

_MODIFIERS = {
    "public", "protected", "private", "static", "final", "abstract",
    "synchronized", "native", "default", "strictfp", "transient", "volatile",
}
_TYPE_KINDS = ("class", "interface", "enum", "record")
_JAVADOC_LIMIT = 4000
_JAVADOC_TAG_LIMIT = 240


def _mask(source: str) -> str:
    """Return a same-length copy with comments and string/char literals blanked.

    Newlines are preserved so indices stay aligned with the original text.
    """
    out = list(source)
    i, n = 0, len(source)
    state = None  # None | 'line' | 'block' | 'string' | 'char'
    while i < n:
        c = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                state = "line"; out[i] = out[i + 1] = " "; i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; out[i] = out[i + 1] = " "; i += 2; continue
            if c == '"':
                state = "string"; out[i] = " "; i += 1; continue
            if c == "'":
                state = "char"; out[i] = " "; i += 1; continue
            i += 1
        elif state == "line":
            if c == "\n":
                state = None
            else:
                out[i] = " "
            i += 1
        elif state == "block":
            if c == "*" and nxt == "/":
                out[i] = out[i + 1] = " "; state = None; i += 2; continue
            if c != "\n":
                out[i] = " "
            i += 1
        elif state == "string":
            if c == "\\":
                out[i] = out[i + 1] = " "; i += 2; continue
            if c == '"':
                out[i] = " "; state = None; i += 1; continue
            out[i] = " "; i += 1
        elif state == "char":
            if c == "\\":
                out[i] = out[i + 1] = " "; i += 2; continue
            if c == "'":
                out[i] = " "; state = None; i += 1; continue
            out[i] = " "; i += 1
    return "".join(out)


def _strip_annotations(sig: str) -> str:
    prev = None
    while prev != sig:
        prev = sig
        sig = re.sub(r"^\s*@\w+(\s*\([^()]*\))?\s*", "", sig)
    return sig


def _strip_generics(text: str) -> str:
    # remove balanced <...> groups (best-effort, handles one level of nesting)
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"<[^<>]*>", " ", text)
    return text


def _clean_javadoc(raw: str) -> Optional[str]:
    """Return a compact Javadoc body from the last /** ... */ before a member."""
    matches = list(re.finditer(r"/\*\*(.*?)\*/", raw, re.DOTALL))
    if not matches:
        return None
    body = matches[-1].group(1)
    lines = []
    for line in body.splitlines():
        line = re.sub(r"^\s*\*\s?", "", line).strip()
        if line:
            lines.append(line)
    text = " ".join(lines).strip()
    return text[:_JAVADOC_LIMIT] if text else None


def _javadoc_tag(javadoc: Optional[str], tag: str) -> Optional[str]:
    if not javadoc:
        return None
    m = re.search(rf"@{tag}\s+(.*?)(?=\s+@\w+\s+|$)", javadoc)
    if not m:
        return None
    text = " ".join(m.group(1).split())
    if len(text) > _JAVADOC_TAG_LIMIT:
        text = text[:_JAVADOC_TAG_LIMIT].rstrip() + "..."
    return text or None


def _javadoc_throws(javadoc: Optional[str]) -> List[str]:
    if not javadoc:
        return []
    out: List[str] = []
    for m in re.finditer(r"@(throws|exception)\s+(.*?)(?=\s+@\w+\s+|$)", javadoc):
        text = " ".join(m.group(2).split())
        if len(text) > _JAVADOC_TAG_LIMIT:
            text = text[:_JAVADOC_TAG_LIMIT].rstrip() + "..."
        if text:
            out.append(text)
    return out


def _body_throws(source: str) -> List[str]:
    """Best-effort exception classes thrown directly in this method body."""
    masked = _mask(source)
    seen = set()
    out: List[str] = []
    for m in re.finditer(r"\bthrow\s+new\s+([\w.$]+)\b", masked):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _split_top_level(text: str) -> List[str]:
    parts, depth, buf = [], 0, []
    for ch in text:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def _parse_params(param_str: str) -> List[JavaParam]:
    param_str = param_str.strip()
    if not param_str:
        return []
    params: List[JavaParam] = []
    for raw in _split_top_level(param_str):
        tokens = raw.replace("final", " ").split()
        if len(tokens) < 2:
            continue
        name = tokens[-1].replace("...", "")
        ptype = " ".join(tokens[:-1])
        params.append(JavaParam(type=ptype, name=name))
    return params


def _find_primary_type(masked: str) -> Optional[Tuple[str, str, int]]:
    """Return (kind, name, body_open_brace_index) for the first top-level type."""
    depth = 0
    for m in re.finditer(r"\b(class|interface|enum|record)\s+(\w+)", masked):
        # ensure declaration sits at top level (brace depth 0 before it)
        depth = masked[: m.start()].count("{") - masked[: m.start()].count("}")
        if depth != 0:
            continue
        brace = masked.find("{", m.end())
        if brace == -1:
            continue
        return m.group(1), m.group(2), brace
    return None


def _match_brace(masked: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(masked) - 1


def _classify_member(masked_seg: str, orig_seg: str, class_name: str):
    sig = _strip_annotations(masked_seg).strip()
    if "(" in sig and ")" in sig:
        before = sig[: sig.index("(")]
        params_str = sig[sig.index("(") + 1: sig.rindex(")")]
        after = sig[sig.rindex(")") + 1:]
        before = _strip_generics(before).strip()
        tokens = before.split()
        if not tokens:
            return None
        name = tokens[-1]
        head = tokens[:-1]
        modifiers = [t for t in head if t in _MODIFIERS]
        non_mod = [t for t in head if t not in _MODIFIERS]
        throws = []
        tm = re.search(r"throws\s+([\w.,\s]+)", after)
        if tm:
            throws = [t.strip() for t in tm.group(1).split(",") if t.strip()]
        params = _parse_params(_strip_generics(params_str))
        is_ctor = (name == class_name) and not non_mod
        if is_ctor:
            return JavaConstructor(
                modifiers=modifiers, name=name, params=params,
                signature=" ".join(before.split()), source=orig_seg.strip(),
            )
        return_type = non_mod[-1] if non_mod else "void"
        header_source = orig_seg[:len(masked_seg)]
        javadoc = _clean_javadoc(header_source)
        return JavaMethod(
            modifiers=modifiers, return_type=return_type, name=name,
            params=params, throws=throws,
            javadoc_return=_javadoc_tag(javadoc, "return"),
            javadoc_throws=_javadoc_throws(javadoc),
            body_throws=_body_throws(orig_seg),
            signature=" ".join(before.split()), source=orig_seg.strip(),
        )
    # field (no parens)
    decl = _strip_annotations(masked_seg).strip().rstrip(";")
    decl = decl.split("=")[0].strip()
    decl = _strip_generics(decl)
    tokens = decl.split()
    if len(tokens) < 2:
        return None
    modifiers = [t for t in tokens if t in _MODIFIERS]
    rest = [t for t in tokens if t not in _MODIFIERS]
    if len(rest) < 2:
        return None
    name = rest[-1]
    ftype = " ".join(rest[:-1])
    return JavaField(modifiers=modifiers, type=ftype, name=name,
                     raw=orig_seg.strip().rstrip(";"))


def parse_java(source: str, file_path: Optional[str] = None) -> Optional[JavaClassStructure]:
    masked = _mask(source)

    pkg_match = re.search(r"^\s*package\s+([\w.]+)\s*;", masked, re.MULTILINE)
    package = pkg_match.group(1) if pkg_match else None

    imports = []
    for m in re.finditer(r"^\s*import\s+(static\s+)?([\w.*]+)\s*;", masked, re.MULTILINE):
        imports.append(((m.group(1) or "") + m.group(2)).strip())

    primary = _find_primary_type(masked)
    if primary is None:
        return None
    kind, class_name, body_open = primary
    body_close = _match_brace(masked, body_open)

    fields: List[JavaField] = []
    constructors: List[JavaConstructor] = []
    methods: List[JavaMethod] = []
    nested_classes: List[str] = []

    i = body_open + 1
    seg_start = i
    while i < body_close:
        ch = masked[i]
        if ch == ";":
            member = _classify_member(masked[seg_start:i], source[seg_start:i], class_name)
            _dispatch(member, fields, constructors, methods)
            i += 1
            seg_start = i
            continue
        if ch == "{":
            close = _match_brace(masked, i)
            header = _strip_annotations(masked[seg_start:i])
            nested = re.search(r"\b(?:class|interface|enum|record)\s+(\w+)", header)
            # A nested TYPE header has a type keyword and no method parens before the
            # brace; capturing its name (not misclassifying it as a field) lets the
            # prompt require Owner.Nested qualification.
            if nested and "(" not in header:
                if nested.group(1) not in nested_classes:
                    nested_classes.append(nested.group(1))
            else:
                member = _classify_member(
                    masked[seg_start:i], source[seg_start:close + 1], class_name
                )
                _dispatch(member, fields, constructors, methods)
            i = close + 1
            seg_start = i
            continue
        i += 1

    return JavaClassStructure(
        package=package, imports=imports, class_name=class_name, kind=kind,
        fields=fields, constructors=constructors, methods=methods,
        nested_classes=nested_classes, file_path=file_path,
    )


def _dispatch(member, fields, constructors, methods):
    if isinstance(member, JavaField):
        fields.append(member)
    elif isinstance(member, JavaConstructor):
        constructors.append(member)
    elif isinstance(member, JavaMethod):
        if "public" in member.modifiers or "protected" in member.modifiers:
            methods.append(member)


def extract_test_methods(source: str) -> List[str]:
    """Best-effort list of @Test-annotated method names (any visibility)."""
    masked = _mask(source)
    names: List[str] = []
    for m in re.finditer(r"@Test\b", masked):
        tail = masked[m.end(): m.end() + 400]
        nm = re.search(r"\b(\w+)\s*\(", tail)
        if nm:
            names.append(nm.group(1))
    return names
