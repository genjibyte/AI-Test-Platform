"""Prompt/Context v3 builder (P2-T04, v3).

Renders the bounded Context Snapshot (docs/07 §P4) into a stable prompt. v3
inherits the REAL Phase 2.5 benchmark failure rules (docs/15, docs/16) and adds
contract grounding for the Phase 2.6 oracle/API failures (docs/21). The rules
are split into a SYSTEM block (role + hard rules) and a USER block (grounded
context + output contract); the same snapshot always yields the same prompt.

v3 keeps the v2 failure-bucket rules and adds method-contract grounding for the
real Phase 2.6 failures: declared throws, Javadoc @throws/@return, and direct
``throw new`` facts are rendered as compact evidence instead of dumping whole
method bodies for whole-class targets.

Each rule maps to an observed failure bucket:
  1 import/static-import missing (assertNotSame, Stream)  -> SELF-CONTAINED imports
  2 nested class unqualified (Builder -> Option.Builder)  -> Nested types block + rule
  3 Java source-level (method-local enum)                 -> no method-local types
  4 mock final class (DeprecatedAttributes)               -> conditional mock rule
  5 oracle/expected wrong (WordUtils)                      -> derive-then-assert / skip
  6 exception/API contract wrong (CSVRecord/Option)       -> contract evidence

v3.1 prompt hardening (docs/26 §6) adds rules for the 10-case failure buckets:
  7 overload/generic ambiguity (Options/NumberUtils/BooleanUtils) -> cast null, typed varargs, declared generics
  8 reflection/private-ctor misuse (WordUtils)            -> public observable APIs only
  9 post-construction state guess; doc!=source (Option.getValues) -> skip when state not shown / docs conflict

v3.2 prompt/context hardening (docs/29, driven by the v3.1 10-case review docs/28):
- renders field initializers + bounded constructor bodies so post-construction
  state (e.g. Option argCount) is derivable, not just skipped;
- strengthens overloads for primitive/boxed varargs + null (BooleanUtils);
- skips a method not in the rendered list (CSVRecord putInMap), exact
  string-transformation/entity maps (StringEscapeUtils), and conditional/catch
  body throws (Option clone);
- forbids @Nested so the top-level surefire report is not empty (Validate).
Per-method return-body grounding and an invalid-JSON retry remain deferred (v4).
"""
from __future__ import annotations

from app.models.context_snapshot import ContextSnapshot

# --- SYSTEM block: role + hard rules (deterministic, context-independent) ----
SYSTEM_PROMPT = (
    "Generate ONE JUnit5 test class for ONE target, using ONLY the bounded "
    "context. If an API or behavior is not shown, you do not know it.\n"
    "\n"
    "Hard rules (a violation makes the test worthless):\n"
    "[API grounding]\n"
    "- Use ONLY types, methods, constructors and constants shown. Never invent "
    "methods, overloads, parameters or fields; SKIP unknown APIs into "
    "omitted_uncertain_cases.\n"
    "- Reference nested types as Owner.Nested (e.g. Option.Builder), never bare.\n"
    "- Test only public, observable APIs. Never use reflection "
    "(setAccessible/getDeclared*) or call a private constructor, even if a "
    "neighbor test does, unless the target itself is that constructor's "
    "behavior.\n"
    "- Before calling any method, confirm it appears in the rendered method list "
    "in the context; if it is not listed, it does not exist in this version, so "
    "skip it.\n"
    "[Imports]\n"
    "- test_source must be ONE self-contained compilable file: a package "
    "declaration and EVERY import, including static import for each JUnit "
    "assertion (e.g. Assertions.assertNotSame).\n"
    "[Build and language]\n"
    "- Never declare an enum/class/interface inside a method body. A helper type "
    "must be a private static nested type of the test class.\n"
    "- Obey Java level. For Java 8/1.8, do not use Java 9+ APIs "
    "(List.of/Set.of/Map.of/Stream.ofNullable); use Java 8-compatible code.\n"
    "- Do NOT mock final classes or value objects, and do NOT mock any type "
    "unless a neighbor test mocks it. Do not assume Mockito inline mock-maker; "
    "prefer real instances.\n"
    "- No network, no absolute file paths, no sleeping/time/randomness.\n"
    "[Overloads and generics]\n"
    "- For overloaded methods, never pass a bare null or an untyped array: cast "
    "each null to the intended parameter type (e.g. (String) null) and build "
    "varargs as an explicitly typed array (e.g. new boolean[]{true}). Ambiguous "
    "overloads do not compile.\n"
    "- Respect declared generic types: assign a result to its declared type and "
    "do not assign a wildcard (List<?>) to a concrete generic (List<Option>).\n"
    "- If a method has both primitive and boxed overloads (boolean... vs "
    "Boolean..., or toBoolean(Boolean) vs toBoolean(String)), never call it with "
    "individual values or a bare null: pass ONE explicitly typed array "
    "(new boolean[]{...} or new Boolean[]{...}) and cast null to the exact type "
    "((Boolean) null, (String) null, (Integer) null).\n"
    "[Oracle grounding]\n"
    "- Derive every expected value from EVIDENCE (target source or neighbor "
    "test). If not derivable, SKIP into omitted_uncertain_cases; never guess.\n"
    "- Exception oracles need strong evidence: declared throws, Javadoc @throws, "
    "or neighbor test. A body-contains-throw fact is only supporting evidence and "
    "may be conditional (inside a catch or an if), so it is NOT proof the normal "
    "path throws; do NOT assertThrows from it alone. Otherwise SKIP into "
    "omitted_uncertain_cases.\n"
    "- Do not infer an object's post-construction field/state from constants or "
    "Javadoc alone; if state is not shown by the target source, a neighbor test, "
    "or a constructor body, SKIP it. If Javadoc conflicts with the method's "
    "return type or source (e.g. doc says empty array but source can return "
    "null), treat it as uncertain: SKIP and note it, do not assert the "
    "documented value.\n"
    "- Do not assert exact string-transformation outputs (escaping, entity maps "
    "like &gt;, encoding, formatting) unless the exact expected value is shown in "
    "the target source or a neighbor test; otherwise SKIP.\n"
    "- No tautological assertions such as assertEquals(x, callThatReturnsX()).\n"
    "- Assert observable behavior, not implementation details.\n"
    "[Test strategy]\n"
    "- Use flat @Test methods only; do NOT use @Nested (the build reads the "
    "top-level test report).\n"
    "- Prefer a few high-confidence tests over a large exhaustive suite; one "
    "behavior per test; avoid large shared @BeforeEach; no assertNotNull-only "
    "smoke tests.\n"
)

# --- Output contract (advertised to the model). v2+ grounding metadata. ---
OUTPUT_CONTRACT = (
    "Return ONLY a single JSON object, no prose, no markdown fences, with keys:\n"
    '  "test_source": string    // FULL self-contained JUnit5 test class (package + all imports)\n'
    '  "imports": string[]      // every import in test_source, including static imports\n'
    '  "used_apis": string[]    // each target API you used; each MUST appear in the context above\n'
    '  "behavior_sources": string[]  // for each non-trivial oracle, the evidence you derived it from\n'
    '  "omitted_uncertain_cases": string[]  // cases you skipped instead of guessing\n'
    '  "dependency_assumptions": string[]   // JUnit/Mockito facts you assumed\n'
    '  "risk_flags": string[]   // anything risky you still did (e.g. mocked a type)\n'
    '  "scenarios": string[]    // human-readable scenarios covered\n'
    '  "mocks": string[]        // types mocked (empty unless a neighbor test mocks them)\n'
    '  "notes": string|null     // optional notes\n'
)


def _fields_block(context: ContextSnapshot) -> str:
    if not context.fields:
        return "(none)"
    rows = []
    for f in context.fields:
        head = f"- {' '.join(f.modifiers)} {f.type} {f.name}".strip()
        # v3.2: surface the initializer (constant value / field default) as
        # post-construction state evidence, bounded.
        if "=" in f.raw:
            init = f.raw.split("=", 1)[1].strip()
            if init:
                head += " = " + (init[:80] + "…" if len(init) > 80 else init)
        rows.append(head)
    return "\n".join(rows)


def _ctor_body_excerpt(source: str, limit: int = 240) -> str:
    """v3.2: bounded, single-line constructor body. The field assignments inside
    are the post-construction state evidence (e.g. Option setting argCount)."""
    open_idx = source.find("{")
    if open_idx == -1:
        return ""
    body = source[open_idx + 1:].rstrip()
    if body.endswith("}"):
        body = body[:-1]
    body = " ".join(body.split())  # collapse to one line
    if not body:
        return ""
    return body[:limit] + ("…" if len(body) > limit else "")


def _ctors_block(context: ContextSnapshot) -> str:
    if not context.constructors:
        return "(default constructor only)"
    rows = []
    for c in context.constructors:
        sig = (
            f"- {c.signature}("
            + ", ".join(f"{p.type} {p.name}" for p in c.params)
            + ")"
        )
        body = _ctor_body_excerpt(c.source)
        if body:
            sig += "\n  sets: " + body
        rows.append(sig)
    return "\n".join(rows)


def _methods_block(context: ContextSnapshot) -> str:
    methods = context.class_structure.methods
    if not methods:
        return "(none)"
    rows = []
    for m in methods:
        sig = (
            f"- {m.return_type} {m.name}("
            + ", ".join(f"{p.type} {p.name}" for p in m.params)
            + ")"
        )
        if m.throws:
            sig += " throws " + ", ".join(m.throws)
        facts = []
        if m.javadoc_return:
            facts.append(f"@return {m.javadoc_return}")
        for jt in m.javadoc_throws:
            facts.append(f"@throws {jt}")
        if m.body_throws:
            facts.append("body contains throw: " + ", ".join(m.body_throws))
        if facts:
            sig += "\n  contract: " + " | ".join(facts)
        rows.append(sig)
    return "\n".join(rows)


def _nested_block(context: ContextSnapshot) -> str:
    nested = context.class_structure.nested_classes
    owner = context.class_structure.class_name
    if not nested:
        return "(none)"
    return "\n".join(f"- {owner}.{n}  (write it as {owner}.{n})" for n in nested)


def _deps_block(context: ContextSnapshot) -> str:
    if not context.maven_dependencies:
        return "(none)"
    return "\n".join(
        f"- {d.group_id}:{d.artifact_id}:{d.version or ''} ({d.scope or 'compile'})"
        for d in context.maven_dependencies
    )


def _build_constraints_block(context: ContextSnapshot) -> str:
    bc = context.build_constraints
    if not (bc.java_source or bc.java_target or bc.java_release):
        return "(not declared)"
    rows = []
    if bc.java_source:
        rows.append(f"- maven.compiler.source={bc.java_source}")
    if bc.java_target:
        rows.append(f"- maven.compiler.target={bc.java_target}")
    if bc.java_release:
        rows.append(f"- maven.compiler.release={bc.java_release}")
    return "\n".join(rows)


def _neighbor_block(context: ContextSnapshot) -> str:
    nt = context.neighbor_test
    if not nt.found:
        return "(no neighbor test found — match standard JUnit5 style)"
    methods = ", ".join(nt.test_methods) or "(no @Test methods)"
    head = f"{nt.class_name} [{nt.file_path}] tests: {methods}"
    if nt.source_excerpt:
        head += (
            "\nMirror this file's import/assertion/mock style. If it does not "
            "mock a type, you must not mock it either. Excerpt:\n"
            + nt.source_excerpt.strip()
        )
    return head


def build_system_prompt(context: ContextSnapshot) -> str:
    """The role + hard rules. Context-independent and deterministic."""
    return SYSTEM_PROMPT


def build_user_prompt(context: ContextSnapshot) -> str:
    """The grounded context block + output contract for one target."""
    cs = context.class_structure
    sections = [
        "Generate a JUnit5 unit test for the target below, obeying the rules.",
        "",
        f"# Target class\n{context.target_class}",
        f"# Target method\n{context.target_method or '(whole class)'}",
        f"# Package\n{cs.package or '(default)'}",
        "# Imports available on the target class\n"
        + ("\n".join(context.imports) if context.imports else "(none)"),
        "# Fields (with initializers — post-construction state evidence)\n"
        + _fields_block(context),
        "# Constructors (with body — derive post-construction state from these)\n"
        + _ctors_block(context),
        "# Public/Protected methods and method-contract evidence (use ONLY these)\n"
        + _methods_block(context),
        "# Nested types (reference as Owner.Nested)\n" + _nested_block(context),
        "# Target method source (derive oracles from this)\n"
        + (context.target_method_source or "(not provided — whole-class target)"),
        "# Neighbor test (style + mock reference)\n" + _neighbor_block(context),
        "# Maven dependencies\n" + _deps_block(context),
        "# Build constraints\n" + _build_constraints_block(context),
        "",
        OUTPUT_CONTRACT,
    ]
    return "\n\n".join(sections).strip() + "\n"


def build_prompt(context: ContextSnapshot) -> str:
    """Full prompt = system rules + grounded user context (back-compat single string)."""
    return build_system_prompt(context) + "\n\n" + build_user_prompt(context)
