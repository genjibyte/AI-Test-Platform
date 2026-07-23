"""Report-only Java test framework fact tests."""
from __future__ import annotations

import pytest

from app.report.java_test_framework import (
    JAVA_TEST_FRAMEWORK_FACTS_VERSION,
    JavaTestFrameworkFactsValidationError,
    detect_java_test_framework,
    normalize_java_test_framework_declaration,
)


def test_detects_testng_as_report_only_enterprise_java_framework():
    source = (
        "import org.testng.annotations.Test;\n"
        "import static org.testng.Assert.assertEquals;\n"
        "class CalcNgTest { @Test public void max() { assertEquals(2, 2); } }"
    )

    facts = detect_java_test_framework(test_source=source)

    assert facts["schema_version"] == JAVA_TEST_FRAMEWORK_FACTS_VERSION
    assert facts["framework"] == "testng"
    assert facts["detected_frameworks"] == ["testng"]
    assert facts["support_status"] == "recognized_report_only_enterprise_java_framework"
    assert facts["testng_enterprise_path_visible"] is True
    assert facts["thin_junit_posture"] is True
    assert facts["runtime_actions_allowed_now"] is False
    assert facts["dependency_install_allowed_now"] is False
    assert facts["pom_mutation_allowed_now"] is False
    assert facts["runner_change_allowed_now"] is False
    assert facts["verdict_authority"] is False
    assert facts["trusted_authority"] is False


def test_detects_junit5_as_existing_maven_surefire_path():
    facts = detect_java_test_framework(
        test_source="import org.junit.jupiter.api.Test; class T { @Test void t() {} }",
        dependency_assumptions=["junit-jupiter"],
    )

    assert facts["framework"] == "junit5"
    assert facts["support_status"] == "recognized_existing_maven_surefire_path"
    assert facts["testng_enterprise_path_visible"] is False
    assert facts["runner_family"] == "maven_surefire_jacoco"


def test_declared_testng_can_make_framework_visible_before_source_markers():
    facts = detect_java_test_framework(
        test_source="class T { @Test public void t() {} }",
        declared_framework="testng",
    )

    assert facts["framework"] == "testng"
    assert facts["declared_framework"] == "testng"
    assert facts["detected_frameworks"] == ["unknown"]
    assert facts["declared_matches_detected"] is None
    assert facts["testng_enterprise_path_visible"] is True


def test_mixed_framework_requires_review_when_declared_and_detected_conflict():
    facts = detect_java_test_framework(
        test_source="import org.junit.jupiter.api.Test; class T { @Test void t() {} }",
        declared_framework="testng",
    )

    assert facts["framework"] == "mixed"
    assert facts["declared_framework"] == "testng"
    assert facts["detected_frameworks"] == ["junit5"]
    assert facts["declared_matches_detected"] is False
    assert facts["support_status"] == "mixed_framework_review_required"
    assert facts["runner_change_allowed_now"] is False


def test_unknown_declared_framework_is_rejected():
    with pytest.raises(JavaTestFrameworkFactsValidationError, match="unknown"):
        detect_java_test_framework(declared_framework="spock")


def test_normalizes_public_framework_declaration_aliases():
    assert normalize_java_test_framework_declaration(" Test-NG ") == "testng"
    assert normalize_java_test_framework_declaration("junit_5") == "junit5"
    assert normalize_java_test_framework_declaration(None) is None
