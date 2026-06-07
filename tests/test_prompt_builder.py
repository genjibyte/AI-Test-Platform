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
from app.models.java_source import JavaClassStructure, JavaMethod, JavaParam


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
