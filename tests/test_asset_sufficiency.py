"""Asset Sufficiency Gate tests (docs/55 S1/S2).

Pure, offline, advisory. These tests assert that asset findings are review hints and never imply
accept/reject.
"""

from app.models.context_snapshot import (
    BuildConstraints,
    ContextSnapshot,
    DependencySummary,
    NeighborTestSummary,
)
from app.models.java_source import JavaClassStructure, JavaField, JavaMethod, JavaParam
from app.quality.asset_sufficiency import (
    asset_facts_from_snapshot,
    estimate_asset_sufficiency,
)


def _asset(**overrides):
    args = {
        "test_source": (
            "package com.example;\n"
            "class CalcTest { @org.junit.jupiter.api.Test void t() { "
            "org.junit.jupiter.api.Assertions.assertEquals(2, new Calc().add(1, 1)); } }"
        ),
        "target_class": "com.example.Calc",
        "target_method": "add",
        "quality_gate": {
            "checked": True,
            "status": "PASS",
            "blocking_issues": [],
            "warnings": [],
            "metrics": {"assertions": 1, "weak_assertions": 0},
        },
        "oracle_strength": {"oracle_strength": "structural_ok"},
        "mock_smells": {"counts": {}},
        "grounding": {"behavior_sources": ["Calc.add returns the arithmetic sum"]},
        "preflight": {"status": "PASS", "blocking_issues": []},
        "coverage_delta": {"target_improved": True},
    }
    args.update(overrides)
    return estimate_asset_sufficiency(**args)


def test_weak_oracle_marks_business_oracle_missing_and_manual_first():
    result = _asset(
        test_source="class EmptyTest { @org.junit.jupiter.api.Test void t() {} }",
        quality_gate={
            "checked": True,
            "status": "FAIL",
            "blocking_issues": [{"code": "no_assertions"}],
            "warnings": [],
            "metrics": {"assertions": 0, "weak_assertions": 0},
        },
        oracle_strength={"oracle_strength": "none"},
        grounding={"behavior_sources": []},
    )

    assert result["business_oracle"] == "missing"
    assert result["test_level_recommendation"] == "manual_oracle_first"
    assert any(i["asset"] == "business_oracle" for i in result["missing_assets"])
    assert result["advisory"] is True


def test_real_dependency_marks_external_mock_missing():
    result = _asset(
        test_source=(
            "class T { @org.junit.jupiter.api.Test void t() { "
            "new org.springframework.web.client.RestTemplate(); "
            "org.junit.jupiter.api.Assertions.assertEquals(1, 1); } }"
        ),
        mock_smells={"counts": {"real_dependency": 1}},
    )

    assert result["external_dependency_mock"] == "missing"
    assert any(i["asset"] == "external_dependency_mock" for i in result["missing_assets"])


def test_clean_candidate_keeps_unit_recommendation_and_no_missing_assets():
    result = _asset()

    assert result["business_oracle"] == "sufficient"
    assert result["code_context"] == "sufficient"
    assert result["external_dependency_mock"] == "sufficient"
    assert result["test_level_recommendation"] == "unit"
    assert result["missing_assets"] == []
    assert result["existing_tests"] == "partial"  # S1 cannot see neighbor-test facts yet.


def test_preflight_failure_marks_code_context_missing():
    result = _asset(
        preflight={
            "status": "FAIL",
            "blocking_issues": [{
                "code": "unlisted_target_method",
                "evidence": "Calc.nope()",
            }],
        },
    )

    assert result["code_context"] == "missing"
    assert any(i["asset"] == "code_context" for i in result["missing_assets"])


def test_no_target_coverage_is_code_context_risk_not_verdict():
    result = _asset(coverage_delta={"target_improved": False})

    assert result["code_context"] == "partial"
    assert any(i["asset"] == "code_context" for i in result["risk_notes"])
    assert result["note"].endswith("changes no verdict")


def test_asset_facts_from_snapshot_persists_counts_not_source_excerpts():
    structure = JavaClassStructure(
        package="com.example",
        class_name="Calc",
        fields=[JavaField(type="int", name="scale", raw="private int scale;")],
        methods=[
            JavaMethod(
                return_type="int",
                name="add",
                params=[
                    JavaParam(type="int", name="left"),
                    JavaParam(type="int", name="right"),
                ],
                signature="public int add(int left, int right)",
                source="public int add(int left, int right) { return left + right; }",
            )
        ],
    )
    snapshot = ContextSnapshot(
        target_class="com.example.Calc",
        target_method="add",
        target_method_source="public int add(int left, int right) { return left + right; }",
        class_structure=structure,
        neighbor_test=NeighborTestSummary(
            found=True,
            file_path="src/test/java/com/example/CalcTest.java",
            class_name="CalcTest",
            test_methods=["adds_two_numbers"],
            source_excerpt="SECRET SOURCE EXCERPT",
        ),
        maven_dependencies=[
            DependencySummary(
                group_id="org.springframework",
                artifact_id="spring-webmvc",
                version="6.0.0",
            ),
            DependencySummary(
                group_id="org.postgresql",
                artifact_id="postgresql",
                version="42.7.0",
            ),
        ],
        build_constraints=BuildConstraints(java_source="17"),
    )

    facts = asset_facts_from_snapshot(snapshot)

    assert facts == {
        "neighbor_test_found": True,
        "neighbor_test_methods": 1,
        "dependency_artifacts": ["postgresql", "spring-webmvc"],
        "build_java_source": "17",
        "target_has_method_source": True,
        "target_method_specified": True,
        "target_fields": 1,
        "target_constructors": 0,
        "target_methods": 1,
    }
    assert "source_excerpt" not in facts
    assert "SECRET SOURCE EXCERPT" not in str(facts)


def test_asset_facts_make_existing_tests_sufficient_when_neighbor_methods_exist():
    result = _asset(
        asset_facts={
            "neighbor_test_found": True,
            "neighbor_test_methods": 2,
            "dependency_artifacts": [],
            "target_has_method_source": True,
        },
    )

    assert result["existing_tests"] == "sufficient"
    assert not any(i["asset"] == "existing_tests" for i in result["missing_assets"])


def test_asset_facts_mark_missing_neighbor_tests_as_review_asset_gap():
    result = _asset(
        asset_facts={
            "neighbor_test_found": False,
            "neighbor_test_methods": 0,
            "dependency_artifacts": [],
            "target_has_method_source": True,
        },
    )

    assert result["existing_tests"] == "missing"
    assert any(i["asset"] == "existing_tests" for i in result["missing_assets"])


def test_asset_facts_mark_missing_target_method_source_as_code_context_gap():
    result = _asset(
        asset_facts={
            "neighbor_test_found": True,
            "neighbor_test_methods": 1,
            "dependency_artifacts": [],
            "target_has_method_source": False,
        },
    )

    assert result["code_context"] == "missing"
    assert any(i["asset"] == "code_context" for i in result["missing_assets"])


def test_dependency_artifacts_are_corroborating_not_standalone_risk():
    result = _asset(
        asset_facts={
            "neighbor_test_found": True,
            "neighbor_test_methods": 1,
            "dependency_artifacts": ["postgresql", "spring-webmvc"],
            "target_has_method_source": True,
        },
    )

    assert result["external_dependency_mock"] == "sufficient"
    assert result["test_data"] == "sufficient"
    assert result["db_schema"] == "sufficient"
    assert result["api_schema"] == "sufficient"
    assert result["test_level_recommendation"] == "unit"


def test_dependency_artifacts_corroborate_source_surface_hints():
    result = _asset(
        test_source=(
            "class T { @org.junit.jupiter.api.Test void t() { "
            "new org.springframework.jdbc.core.JdbcTemplate(); "
            "org.junit.jupiter.api.Assertions.assertEquals(1, 1); } }"
        ),
        asset_facts={
            "neighbor_test_found": True,
            "neighbor_test_methods": 1,
            "dependency_artifacts": ["postgresql"],
            "target_has_method_source": True,
        },
    )

    assert result["external_dependency_mock"] == "partial"
    assert result["test_data"] == "partial"
    assert result["db_schema"] == "partial"
    assert result["test_level_recommendation"] == "integration"
    assert any(i.get("evidence") == "db" for i in result["evidence"])


def test_api_target_name_can_recommend_api_without_api_harness():
    result = _asset(
        target_class="com.example.UserController",
        asset_facts={
            "neighbor_test_found": True,
            "neighbor_test_methods": 1,
            "dependency_artifacts": ["spring-webmvc"],
            "target_has_method_source": True,
        },
    )

    assert result["api_schema"] == "partial"
    assert result["test_level_recommendation"] == "api"
    assert result["advisory"] is True
