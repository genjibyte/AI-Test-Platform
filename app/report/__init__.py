"""Surefire parsing and read-only report assembly/presentation helpers."""

from app.report.api_smoke_redlines_report import render_api_smoke_redlines_markdown
from app.report.java_test_framework import (
    JAVA_TEST_FRAMEWORK_FACTS_VERSION,
    JavaTestFrameworkFactsValidationError,
    detect_java_test_framework,
    normalize_java_test_framework_declaration,
)

__all__ = [
    "JAVA_TEST_FRAMEWORK_FACTS_VERSION",
    "JavaTestFrameworkFactsValidationError",
    "detect_java_test_framework",
    "normalize_java_test_framework_declaration",
    "render_api_smoke_redlines_markdown",
]
