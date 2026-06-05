"""Surefire report parsing (P1-T07).

Aggregates all ``surefire-reports/TEST-*.xml`` under a repo (covers multi-module
layouts too) into a structured TestResult. Pure parsing — no classification.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Union

from app.models.test_result import FailedCase, TestResult

_MSG_LIMIT = 500


def _int(value: str | None) -> int:
    try:
        return int(value) if value else 0
    except ValueError:
        return 0


def _suites(root: ET.Element) -> Iterable[ET.Element]:
    tag = root.tag.rsplit("}", 1)[-1]
    if tag == "testsuites":
        return root.findall("testsuite")
    return [root]


def parse_surefire(repo_dir: Union[str, Path]) -> TestResult:
    repo_dir = Path(repo_dir)
    files = sorted(repo_dir.glob("**/surefire-reports/TEST-*.xml"))
    if not files:
        return TestResult(has_reports=False)

    total = failures = errors = skipped = 0
    failed_cases: list[FailedCase] = []

    for path in files:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for suite in _suites(root):
            total += _int(suite.get("tests"))
            failures += _int(suite.get("failures"))
            errors += _int(suite.get("errors"))
            skipped += _int(suite.get("skipped"))
            for tc in suite.findall("testcase"):
                failure = tc.find("failure")
                error = tc.find("error")
                if failure is None and error is None:
                    continue
                node = failure if failure is not None else error
                failed_cases.append(
                    FailedCase(
                        classname=tc.get("classname", ""),
                        name=tc.get("name", ""),
                        type="failure" if failure is not None else "error",
                        message=(node.get("message") or "")[:_MSG_LIMIT],
                    )
                )

    passed = max(total - failures - errors - skipped, 0)
    return TestResult(
        has_reports=True,
        suites=len(files),
        total=total,
        passed=passed,
        failed=failures,
        errors=errors,
        skipped=skipped,
        failed_cases=failed_cases,
    )
