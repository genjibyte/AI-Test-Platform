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


# --- docs/36: overload-ambiguity detection (Shape A bare-null, Shape B mix) ----

def _run(source: str, methods: list[JavaMethod],
         target: str = "org.apache.commons.lang3.BooleanUtils"):
    ctx = ContextSnapshot(
        target_class=target,
        class_structure=JavaClassStructure(
            package=target.rsplit(".", 1)[0] if "." in target else "",
            class_name=target.rsplit(".", 1)[-1], methods=methods,
        ),
    )
    res = evaluate_generated_test_preflight(source, ctx)
    return {i.code for i in res.blocking_issues}, res.status


def test_preflight_flags_bare_null_reference_overload_ambiguity():
    # toBoolean(null): Boolean vs String both accept null -> ambiguous (Shape A).
    methods = [_method("toBoolean", ["boolean"]), _method("toBoolean", ["Boolean"]),
               _method("toBoolean", ["String"])]
    codes, _ = _run("class T { void t() { BooleanUtils.toBoolean(null); } }", methods)
    assert "ambiguous_null_overload_call" in codes


def test_preflight_allows_bare_null_single_reference_overload():
    # Only String accepts null (boolean cannot) -> unambiguous, must not flag.
    methods = [_method("toBoolean", ["boolean"]), _method("toBoolean", ["String"])]
    _, status = _run("class T { void t() { BooleanUtils.toBoolean(null); } }", methods)
    assert status == "PASS"


def test_preflight_flags_mixed_boxed_primitive_overload():
    # toBoolean(Integer.valueOf(3), 1, 2): boxed + primitive in an int/Integer family.
    methods = [_method("toBoolean", ["int", "int", "int"]),
               _method("toBoolean", ["Integer", "Integer", "Integer"])]
    codes, _ = _run(
        "class T { void t() { BooleanUtils.toBoolean(Integer.valueOf(3), 1, 2); } }",
        methods,
    )
    assert "ambiguous_boxed_primitive_overload_call" in codes


def test_preflight_allows_all_primitive_or_all_boxed_call():
    methods = [_method("toBoolean", ["int", "int", "int"]),
               _method("toBoolean", ["Integer", "Integer", "Integer"])]
    prim, _ = _run("class T { void t() { BooleanUtils.toBoolean(1, 2, 3); } }", methods)
    boxed, _ = _run(
        "class T { void t() { BooleanUtils.toBoolean(Integer.valueOf(1), "
        "Integer.valueOf(2), Integer.valueOf(3)); } }", methods)
    assert prim == set() and boxed == set()


def test_preflight_overload_ambiguity_unknown_args_defer_to_maven():
    # Variables are UNKNOWN -> never spuriously flagged (conservative, FP-averse).
    methods = [_method("toBoolean", ["int", "int", "int"]),
               _method("toBoolean", ["Integer", "Integer", "Integer"])]
    _, status = _run("class T { void t() { BooleanUtils.toBoolean(a, b, c); } }", methods)
    assert status == "PASS"


def test_preflight_shape_b_no_flag_when_reference_overload_is_not_wrapper_family():
    # f(int,int) / f(String,String); f(Integer.valueOf(1), 2) binds f(int,int) and
    # compiles. String is not the wrapper of int, so this must NOT be flagged.
    _, status = _run(
        "class X { void t() { T.f(Integer.valueOf(1), 2); } }",
        [_method("f", ["int", "int"]), _method("f", ["String", "String"])],
        target="pkg.T",
    )
    assert status == "PASS"


def test_preflight_shape_a_defers_when_another_arg_disambiguates():
    # f(String,int) / f(Integer,String); f(null, 1) -> the int `1` excludes
    # f(Integer,String), so Java binds f(String,int). Must NOT be flagged.
    _, status = _run(
        "class X { void t() { T.f(null, 1); } }",
        [_method("f", ["String", "int"]), _method("f", ["Integer", "String"])],
        target="pkg.T",
    )
    assert status == "PASS"
