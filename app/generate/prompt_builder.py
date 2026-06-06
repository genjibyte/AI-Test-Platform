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
    "[Oracle grounding]\n"
    "- Derive every expected value from EVIDENCE (target source or neighbor "
    "test). If not derivable, SKIP into omitted_uncertain_cases; never guess.\n"
    "- Exception oracles need method-contract evidence: throws, Javadoc "
    "@throws, body throw, or neighbor test. Use assertThrows only then; "
    "otherwise SKIP into omitted_uncertain_cases.\n"
    "- No tautological assertions such as assertEquals(x, callThatReturnsX()).\n"
    "- Assert observable behavior, not implementation details.\n"
    "[Test strategy]\n"
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
    return "\n".join(
        f"- {' '.join(f.modifiers)} {f.type} {f.name}".strip()
        for f in context.fields
    )


def _ctors_block(context: ContextSnapshot) -> str:
    if not context.constructors:
        return "(default constructor only)"
    return "\n".join(f"- {c.signature}(" + ", ".join(
        f"{p.type} {p.name}" for p in c.params) + ")" for c in context.constructors)


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
            facts.append("body throws: " + ", ".join(m.body_throws))
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
        "# Fields\n" + _fields_block(context),
        "# Constructors\n" + _ctors_block(context),
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
