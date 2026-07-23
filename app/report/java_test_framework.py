"""Report-only Java test framework facts.

This helper keeps the Java execution kernel framework-aware without changing
the runner. Maven/Surefire/JaCoCo stays the current evidence path; JUnit and
TestNG are detected only as review metadata.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

JAVA_TEST_FRAMEWORK_FACTS_VERSION = "java_test_framework_facts.v1"

KNOWN_FRAMEWORKS = ("junit4", "junit5", "testng", "unknown", "mixed")
_DECLARED_FRAMEWORKS = {"junit4", "junit5", "testng", "unknown"}

_FRAMEWORK_MARKERS = {
    "testng": (
        "org.testng",
        "testng.annotations",
        "org.testng.Assert",
        "org.testng.asserts",
    ),
    "junit5": (
        "org.junit.jupiter",
        "junit-jupiter",
        "org.junit.platform",
    ),
    "junit4": (
        "org.junit.Test",
        "org.junit.Assert",
        "junit:junit",
        "<artifactId>junit</artifactId>",
    ),
}

_SUPPORT_STATUS = {
    "junit4": "recognized_existing_maven_surefire_path",
    "junit5": "recognized_existing_maven_surefire_path",
    "testng": "recognized_report_only_enterprise_java_framework",
    "unknown": "unknown_framework_review_required",
    "mixed": "mixed_framework_review_required",
}


class JavaTestFrameworkFactsValidationError(ValueError):
    """Raised when Java test framework metadata is invalid."""


def normalize_java_test_framework_declaration(value: str | None) -> str | None:
    """Normalize a caller-declared Java test framework value.

    This validates metadata only. It grants no runner, dependency, POM, verdict,
    or trust authority.
    """
    return _normalize_declared_framework(value)


def detect_java_test_framework(
    *,
    test_source: str | None = None,
    dependency_assumptions: Iterable[str] | None = None,
    asset_facts: Mapping[str, Any] | None = None,
    declared_framework: str | None = None,
) -> dict[str, Any]:
    """Return compact report-only Java test framework facts.

    Detection is heuristic and advisory. It never installs dependencies,
    changes candidate kind, chooses a runner, or grants verdict/trust authority.
    """
    declared = _normalize_declared_framework(declared_framework)
    detected = _detected_frameworks(
        test_source=test_source,
        dependency_assumptions=dependency_assumptions,
        asset_facts=asset_facts,
    )
    framework = _resolved_framework(detected, declared)

    return {
        "schema_version": JAVA_TEST_FRAMEWORK_FACTS_VERSION,
        "advisory": True,
        "report_only": True,
        "framework": framework,
        "declared_framework": declared,
        "detected_frameworks": detected,
        "declared_matches_detected": _declared_matches_detected(declared, detected),
        "runner_family": "maven_surefire_jacoco",
        "support_status": _SUPPORT_STATUS[framework],
        "thin_junit_posture": True,
        "testng_enterprise_path_visible": "testng" in detected or declared == "testng",
        "owner_gate_required_before": [
            "dependency_install",
            "pom_mutation",
            "runner_change",
            "framework_specific_generator_tuning",
            "verdict_or_trust_change",
        ],
        "runtime_actions_allowed_now": False,
        "dependency_install_allowed_now": False,
        "pom_mutation_allowed_now": False,
        "runner_change_allowed_now": False,
        "verdict_authority": False,
        "trusted_authority": False,
        "note": (
            "Framework facts only. JUnit is the current compatibility path, "
            "TestNG is recognized for enterprise Java review, and Maven/Surefire "
            "remains the evidence runner unless an owner-gated design changes it."
        ),
    }


def _normalize_declared_framework(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise JavaTestFrameworkFactsValidationError(
            "declared_framework must be a non-empty string"
        )
    normalized = value.strip().lower().replace("_", "-")
    aliases = {
        "junit": "junit5",
        "junit-4": "junit4",
        "junit4": "junit4",
        "junit-5": "junit5",
        "junit5": "junit5",
        "jupiter": "junit5",
        "test-ng": "testng",
        "testng": "testng",
        "unknown": "unknown",
    }
    if normalized not in aliases:
        allowed = ", ".join(sorted(_DECLARED_FRAMEWORKS))
        raise JavaTestFrameworkFactsValidationError(
            f"unknown declared_framework {value!r}; allowed: {allowed}"
        )
    return aliases[normalized]


def _detected_frameworks(
    *,
    test_source: str | None,
    dependency_assumptions: Iterable[str] | None,
    asset_facts: Mapping[str, Any] | None,
) -> list[str]:
    haystack = " ".join([
        test_source or "",
        " ".join(str(item) for item in (dependency_assumptions or ())),
        _asset_facts_text(asset_facts),
    ]).lower()
    detected = [
        framework
        for framework, markers in _FRAMEWORK_MARKERS.items()
        if any(marker.lower() in haystack for marker in markers)
    ]
    return detected or ["unknown"]


def _asset_facts_text(asset_facts: Mapping[str, Any] | None) -> str:
    if not isinstance(asset_facts, Mapping):
        return ""
    chunks: list[str] = []
    for key in ("maven_dependencies", "dependency_artifacts", "dependencies"):
        value = asset_facts.get(key)
        if isinstance(value, list):
            chunks.extend(str(item) for item in value)
    return " ".join(chunks)


def _resolved_framework(detected: list[str], declared: str | None) -> str:
    concrete = [item for item in detected if item != "unknown"]
    if len(set(concrete)) > 1:
        return "mixed"
    if declared and declared != "unknown":
        if not concrete or concrete == [declared]:
            return declared
        return "mixed"
    if concrete:
        return concrete[0]
    return "unknown"


def _declared_matches_detected(
    declared: str | None,
    detected: list[str],
) -> bool | None:
    if declared is None or declared == "unknown":
        return None
    concrete = [item for item in detected if item != "unknown"]
    if not concrete:
        return None
    return set(concrete) == {declared}
