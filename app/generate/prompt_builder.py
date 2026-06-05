"""Deterministic prompt builder (P2-T04 seam).

Renders the bounded Context Snapshot (docs/07 §P4) into a stable prompt that
instructs the model to return ONLY the ``LLMTestPayload`` JSON. Deterministic:
the same snapshot always yields the same prompt (stable ordering, no timestamps,
no randomness) so the contract can be reviewed and snapshot-tested.
"""
from __future__ import annotations

from app.models.context_snapshot import ContextSnapshot

# The output contract advertised to the model. Mirrors app.llm.schema.LLMTestPayload.
OUTPUT_CONTRACT = (
    "Return ONLY a single JSON object, no prose, no markdown fences, with keys:\n"
    '  "imports": string[]      // fully-qualified imports the test needs\n'
    '  "test_source": string    // the FULL JUnit5 test class source\n'
    '  "scenarios": string[]    // human-readable scenarios covered\n'
    '  "mocks": string[]        // types mocked with Mockito (may be empty)\n'
    '  "notes": string|null     // optional notes\n'
)

RULES = (
    "Rules:\n"
    "- Use JUnit5 (org.junit.jupiter) and Mockito only.\n"
    "- Generate tests ONLY; never modify production code or existing tests.\n"
    "- Cover happy path AND edge/exception cases where applicable.\n"
    "- Use meaningful assertions (not just assertNotNull).\n"
    "- Do not invent constructors, dependencies, return types, or imports beyond the context.\n"
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
    return "\n".join(
        f"- {m.return_type} {m.name}(" + ", ".join(
            f"{p.type} {p.name}" for p in m.params) + ")"
        for m in methods
    )


def _deps_block(context: ContextSnapshot) -> str:
    if not context.maven_dependencies:
        return "(none)"
    return "\n".join(
        f"- {d.group_id}:{d.artifact_id}:{d.version or ''} ({d.scope or 'compile'})"
        for d in context.maven_dependencies
    )


def _neighbor_block(context: ContextSnapshot) -> str:
    nt = context.neighbor_test
    if not nt.found:
        return "(no neighbor test found)"
    methods = ", ".join(nt.test_methods) or "(no @Test methods)"
    return f"{nt.class_name} [{nt.file_path}] tests: {methods}"


def build_prompt(context: ContextSnapshot) -> str:
    cs = context.class_structure
    sections = [
        "You are generating a JUnit5 unit test for one Java target.",
        "",
        f"# Target class\n{context.target_class}",
        f"# Target method\n{context.target_method or '(whole class)'}",
        f"# Package\n{cs.package or '(default)'}",
        "# Imports\n" + ("\n".join(context.imports) if context.imports else "(none)"),
        "# Fields\n" + _fields_block(context),
        "# Constructors\n" + _ctors_block(context),
        "# Public/Protected methods\n" + _methods_block(context),
        "# Target method source\n"
        + (context.target_method_source or "(not provided)"),
        "# Neighbor test (style reference)\n" + _neighbor_block(context),
        "# Maven dependencies\n" + _deps_block(context),
        "",
        RULES,
        OUTPUT_CONTRACT,
    ]
    return "\n\n".join(sections).strip() + "\n"
