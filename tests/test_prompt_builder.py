"""Prompt/Context v3 tests (P2-T04 v3).

Each assertion pins a v2/v3 rule to the real benchmark failure bucket it targets
(docs/15, docs/16, docs/21). Pure-text over a synthetic snapshot — no model, no I/O.
"""
from app.generate.prompt_builder import (
    build_prompt,
    build_system_prompt,
    build_user_prompt,
)
from app.models.context_snapshot import (
    BuildConstraints,
    ContextSnapshot,
    NeighborTestSummary,
)
from app.models.java_source import (
    JavaClassStructure,
    JavaConstructor,
    JavaField,
    JavaMethod,
    JavaParam,
)


def _ctx(**over):
    structure = JavaClassStructure(
        package="org.apache.commons.cli",
        imports=["java.util.List"],
        class_name="Option",
        nested_classes=["Builder"],
        methods=[
            JavaMethod(return_type="Builder", name="builder",
                       params=[JavaParam(type="String", name="opt")],
                       throws=["IllegalArgumentException"],
                       javadoc_return="a builder for the option",
                       javadoc_throws=[
                           "IllegalArgumentException if opt is blank"
                       ],
                       body_throws=["UnsupportedOperationException"],
                       signature="static Builder builder", source=""),
        ],
    )
    base = dict(
        target_class="org.apache.commons.cli.Option",
        target_method=None,
        target_method_source=None,
        class_structure=structure,
        neighbor_test=NeighborTestSummary(
            found=True, class_name="OptionTest", file_path="OptionTest.java",
            test_methods=["testBuilder"], source_excerpt="class OptionTest { }",
        ),
        build_constraints=BuildConstraints(java_source="1.8", java_target="1.8"),
    )
    base.update(over)
    return ContextSnapshot(**base)


def test_system_and_user_split_compose_into_full_prompt():
    ctx = _ctx()
    assert build_prompt(ctx) == build_system_prompt(ctx) + "\n\n" + build_user_prompt(ctx)


def test_deterministic():
    ctx = _ctx()
    assert build_prompt(ctx) == build_prompt(ctx)


def test_bucket1_self_contained_imports_rule():
    sys = build_system_prompt(_ctx())
    assert "self-contained" in sys
    assert "static import" in sys
    assert "assertNotSame" in sys  # the exact missing-import seen in the benchmark


def test_bucket2_nested_class_qualification():
    p = build_prompt(_ctx())
    assert "Owner.Nested" in p
    assert "Option.Builder" in p          # nested types listed qualified in context


def test_bucket3_no_method_local_types():
    sys = build_system_prompt(_ctx())
    assert "inside a method body" in sys
    assert "private static nested type" in sys


def test_bucket3_java8_source_level_constraints():
    p = build_prompt(_ctx())
    assert "maven.compiler.source=1.8" in p
    assert "List.of" in p
    assert "Java 8-compatible" in p


def test_bucket4_conditional_mock_rule():
    sys = build_system_prompt(_ctx())
    assert "final classes" in sys
    assert "unless a neighbor test mocks it" in sys
    assert "inline mock-maker" in sys     # the actual Mockito mechanism


def test_bucket5_oracle_grounding_and_skip():
    sys = build_system_prompt(_ctx())
    assert "Derive every expected value from EVIDENCE" in sys
    assert "omitted_uncertain_cases" in sys
    assert "assertThrows" in sys
    assert "body-contains-throw fact is only supporting evidence" in sys
    assert "tautological" in sys


def test_v3_method_contract_evidence_rendered():
    p = build_user_prompt(_ctx())
    assert "method-contract evidence" in p
    assert "builder(String opt) throws IllegalArgumentException" in p
    assert "@return a builder for the option" in p
    assert "@throws IllegalArgumentException if opt is blank" in p
    assert "body contains throw: UnsupportedOperationException" in p


def test_v3_1_overload_and_generics_disambiguation():
    # 10-case compile fails: Options wildcard, NumberUtils null overload, BooleanUtils varargs.
    sys = build_system_prompt(_ctx())
    assert "Overloads and generics" in sys
    assert "(String) null" in sys                       # cast null to the intended overload
    assert "new boolean[]{true}" in sys                 # explicitly typed varargs array
    assert "List<?>" in sys and "List<Option>" in sys   # no wildcard -> concrete generic


def test_v3_1_public_apis_no_reflection_or_private_ctor():
    # 10-case WordUtils FAIL: reflection / private-constructor test is not useful.
    sys = build_system_prompt(_ctx())
    assert "public, observable APIs" in sys
    assert "reflection" in sys
    assert "private constructor" in sys


def test_v3_1_post_construction_state_and_doc_source_conflict():
    # 10-case Option.getValues(): Javadoc says empty array but impl returns null.
    sys = build_system_prompt(_ctx())
    assert "post-construction field/state" in sys
    assert "Javadoc conflicts" in sys
    assert "do not assert the documented value" in sys


def test_v3_2_field_initializers_and_constructor_body_grounding():
    # 10-case Option: new Option("a", true, "desc").getArgs() is 1 (set by the
    # constructor), not the field default UNINITIALIZED. v3.2 renders field
    # initializers + the constructor body so that state is derivable, not guessed.
    structure = JavaClassStructure(
        package="org.apache.commons.cli", class_name="Option",
        fields=[
            JavaField(modifiers=["private", "static", "final"], type="int",
                      name="UNINITIALIZED",
                      raw="private static final int UNINITIALIZED = -1"),
            JavaField(modifiers=["private"], type="int", name="argCount",
                      raw="private int argCount = UNINITIALIZED"),
        ],
        constructors=[
            JavaConstructor(modifiers=["public"], name="Option",
                params=[JavaParam(type="String", name="opt"),
                        JavaParam(type="boolean", name="hasArg")],
                signature="public Option",
                source="public Option(String opt, boolean hasArg) "
                       "{ this.opt = opt; if (hasArg) this.argCount = 1; }"),
        ],
        methods=[],
    )
    # context_collector copies these to the snapshot top level; mirror that here.
    p = build_user_prompt(_ctx(
        class_structure=structure,
        fields=structure.fields,
        constructors=structure.constructors,
    ))
    assert "UNINITIALIZED = -1" in p                       # constant value surfaced
    assert "argCount = UNINITIALIZED" in p                 # field default surfaced
    assert "if (hasArg) this.argCount = 1" in p            # constructor sets the state
    assert "post-construction state" in p                  # header signals the purpose


def test_v3_2_constructor_body_ignores_leading_javadoc_braces():
    structure = JavaClassStructure(
        package="org.apache.commons.cli", class_name="Option",
        constructors=[
            JavaConstructor(
                modifiers=["public"], name="Option",
                params=[JavaParam(type="String", name="opt")],
                signature="public Option",
                source=(
                    "/** @throws IllegalArgumentException if {@code opt} is blank. */\n"
                    "public Option(String opt) { // validate before assignment\n"
                    " this.option = opt; }"
                ),
            ),
        ],
        methods=[],
    )
    p = build_user_prompt(_ctx(
        class_structure=structure,
        constructors=structure.constructors,
    ))
    assert "sets: this.option = opt;" in p
    assert "{@code opt}" not in p
    assert "validate before assignment" not in p


def test_v3_2_overload_varargs_primitive_boxed_strengthened():
    # 10-case BooleanUtils: and/or/xor varargs + toBoolean(null) primitive/boxed ambiguity.
    sys = build_system_prompt(_ctx())
    assert "primitive and boxed overloads" in sys
    assert "new Boolean[]" in sys
    assert "(Boolean) null" in sys


def test_v3_2_method_must_be_in_rendered_list():
    # 10-case CSVRecord: called putInMap(...) which is not on the class in this version.
    sys = build_system_prompt(_ctx())
    assert "confirm it appears in the rendered method list" in sys


def test_v3_2_conditional_body_throw_not_oracle():
    # 10-case Option.testCloneThrows: conditional/catch throw misused as a normal-path oracle.
    sys = build_system_prompt(_ctx())
    assert "may be conditional" in sys
    assert "body-contains-throw fact is only supporting evidence" in sys  # v3.1 phrase kept


def test_v3_2_no_exact_string_transformation_guess():
    # 10-case StringEscapeUtils: guessed exact XML entity maps (&gt;).
    sys = build_system_prompt(_ctx())
    assert "string-transformation" in sys
    assert "&gt;" in sys


def test_v3_2_flat_tests_no_nested():
    # 10-case Validate: @Nested tests ran but the top-level surefire report was empty.
    sys = build_system_prompt(_ctx())
    assert "do NOT use @Nested" in sys


def test_api_grounding_only_context_apis():
    sys = build_system_prompt(_ctx())
    assert "Use ONLY types" in sys
    assert "Never invent methods" in sys


def test_neighbor_style_imitation_present():
    p = build_prompt(_ctx())
    assert "OptionTest" in p
    assert "If it does not mock a type, you must not mock it" in p


def test_output_contract_has_grounding_metadata_keys():
    p = build_prompt(_ctx())
    for key in ("used_apis", "behavior_sources", "omitted_uncertain_cases",
                "dependency_assumptions", "risk_flags"):
        assert f'"{key}"' in p
    assert '"test_source"' in p


def test_whole_class_target_has_no_method_source():
    # whole-class target -> no per-method body, so the prompt must say so
    assert "whole-class target" in build_user_prompt(_ctx(target_method=None))
