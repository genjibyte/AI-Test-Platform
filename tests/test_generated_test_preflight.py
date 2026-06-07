from app.models.context_snapshot import ContextSnapshot
from app.models.java_source import JavaClassStructure, JavaMethod, JavaParam
from app.quality.generated_test_preflight import evaluate_generated_test_preflight


def _method(name: str, params: list[str]) -> JavaMethod:
    return JavaMethod(
        return_type="Boolean",
        name=name,
        params=[JavaParam(type=p, name=f"p{i}") for i, p in enumerate(params)],
        signature=f"public static Boolean {name}",
        source="",
    )


def _ctx() -> ContextSnapshot:
    return ContextSnapshot(
        target_class="org.apache.commons.lang3.BooleanUtils",
        class_structure=JavaClassStructure(
            package="org.apache.commons.lang3",
            class_name="BooleanUtils",
            methods=[
                _method("toBooleanObject", ["int"]),
                _method("toBooleanObject", ["int", "int", "int", "int"]),
                _method("and", ["boolean..."]),
                _method("and", ["Boolean..."]),
            ],
        ),
    )


def _codes(source: str) -> set[str]:
    result = evaluate_generated_test_preflight(source, _ctx())
    return {issue.code for issue in result.blocking_issues}


def test_preflight_allows_listed_target_method_arity():
    result = evaluate_generated_test_preflight(
        "class T { void t() { BooleanUtils.toBooleanObject(1, 1, 0, 2); } }",
        _ctx(),
    )
    assert result.status == "PASS"
    assert result.metrics["target_class_calls"] == 1


def test_preflight_blocks_unlisted_target_method_arity():
    codes = _codes(
        "class T { void t() { BooleanUtils.toBooleanObject(1, 1, 0); } }"
    )
    assert "unlisted_target_overload_arity" in codes


def test_preflight_blocks_unlisted_target_method_name():
    codes = _codes("class T { void t() { BooleanUtils.missing(1); } }")
    assert "unlisted_target_method" in codes


def test_preflight_blocks_ambiguous_primitive_boxed_varargs_individual_values():
    codes = _codes("class T { void t() { BooleanUtils.and(true, true); } }")
    assert "ambiguous_varargs_overload_call" in codes


def test_preflight_allows_ambiguous_varargs_pair_when_called_with_one_array():
    result = evaluate_generated_test_preflight(
        "class T { void t() { boolean[] values = {true, true}; BooleanUtils.and(values); } }",
        _ctx(),
    )
    assert result.status == "PASS"


def test_preflight_ignores_comments_strings_and_instance_calls():
    result = evaluate_generated_test_preflight(
        '''
        class T {
          void t() {
            // BooleanUtils.missing(1)
            String s = "BooleanUtils.toBooleanObject(1, 1, 0)";
            record.get("A");
          }
        }
        ''',
        _ctx(),
    )
    assert result.status == "PASS"
    assert result.metrics["target_class_calls"] == 0


def test_preflight_allows_fixed_arity_overload_alongside_varargs_pair():
    # If a fixed-arity overload matches the call arity, Java binds to it before a
    # varargs overload (JLS 15.12.2), so the boolean.../Boolean... pair is NOT
    # ambiguous for this call and the gate must not skip a compilable test.
    ctx = ContextSnapshot(
        target_class="org.apache.commons.lang3.BooleanUtils",
        class_structure=JavaClassStructure(
            package="org.apache.commons.lang3",
            class_name="BooleanUtils",
            methods=[
                _method("and", ["boolean", "boolean"]),  # fixed 2-arg overload
                _method("and", ["boolean..."]),
                _method("and", ["Boolean..."]),
            ],
        ),
    )
    result = evaluate_generated_test_preflight(
        "class T { void t() { BooleanUtils.and(true, true); } }", ctx,
    )
    assert result.status == "PASS"


def test_preflight_checks_fqcn_qualified_calls():
    # Fully-qualified target calls are validated the same as simple-name calls.
    codes = _codes(
        "class T { void t() { org.apache.commons.lang3.BooleanUtils.missing(1); } }"
    )
    assert "unlisted_target_method" in codes
