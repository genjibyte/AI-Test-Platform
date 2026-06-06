"""Execute the generated test, reusing the Phase 1 runner (P2-T07).

Runs the *full* module test suite WITH JaCoCo coverage on the workspace that
already contains the freshly written ``<Target>AiGeneratedTest.java``. Running
the full suite (original + generated) gives the "after" coverage that P2-T08
compares against the Phase 1 baseline.

The generated test's own outcome is then isolated by parsing ONLY its Surefire
report (``TEST-<fqcn>.xml``), so a pre-existing unrelated failure elsewhere in
the suite never masks whether the generated test itself compiled / ran / passed.

Phase 2 red-lines honored here: no repair, no retry, no pom/source edits, no
weakening of assertions — this module only runs and records facts.
"""
from __future__ import annotations

import enum
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Sequence, Union

from pydantic import BaseModel

from app.build.maven_runner import BuildOutcome
from app.coverage.jacoco_parser import parse_jacoco
from app.coverage.jacoco_runner import run_mvn_test_with_coverage
from app.llm.schema import TestGenerationResult
from app.report.surefire_parser import parse_surefire
from app.runtime.workspace import Workspace


class GenTestOutcome(str, enum.Enum):
    """Outcome of the *generated* test specifically (not the whole suite)."""

    PASS = "PASS"                      # ran, zero failures/errors
    TEST_FAILURE = "TEST_FAILURE"      # ran, had assertion failures or errors
    COMPILE_FAILURE = "COMPILE_FAILURE"  # generated test broke test compilation
    NO_TESTS = "NO_TESTS"              # compiled & ran but produced no test cases
    BUILD_ERROR = "BUILD_ERROR"        # timeout / unexpected build break
    NO_MAVEN = "NO_MAVEN"              # maven unavailable


class GenExecResult(BaseModel):
    """Facts from one execution of the generated test. No verdict (Phase 4)."""

    __test__ = False  # not a pytest test class despite the 'Test' suffix above

    generated_class: str               # fully-qualified generated test class
    gen_outcome: GenTestOutcome
    build_outcome: str                 # whole-suite BuildOutcome.value
    # generated-test-only counts (from its own surefire report)
    gen_report_found: bool = False
    gen_total: int = 0
    gen_passed: int = 0
    gen_failed: int = 0
    gen_errors: int = 0
    gen_skipped: int = 0
    # whole-suite facts (for context / report)
    suite_result: dict                 # TestResult.model_dump()
    after_coverage: dict               # Coverage.summary()
    log_path: Optional[str] = None
    exec_record: Optional[dict] = None  # ExecRecord.trimmed()


def fqcn_of(result: TestGenerationResult) -> str:
    """Fully-qualified name of the generated test class."""
    if result.package:
        return f"{result.package}.{result.test_class_name}"
    return result.test_class_name


def _int(value: Optional[str]) -> int:
    try:
        return int(value) if value else 0
    except ValueError:
        return 0


def _parse_generated_report(repo_dir: Path, fqcn: str) -> Optional[dict]:
    """Parse the single ``TEST-<fqcn>.xml`` report for the generated class.

    Returns counts dict, or None when no report exists for that class.
    """
    for path in sorted(repo_dir.glob(f"**/surefire-reports/TEST-{fqcn}.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        # a TEST-*.xml root is a single <testsuite>
        return {
            "total": _int(root.get("tests")),
            "failures": _int(root.get("failures")),
            "errors": _int(root.get("errors")),
            "skipped": _int(root.get("skipped")),
        }
    return None


def _classify(repo_dir: Path, fqcn: str, outcome: BuildOutcome) -> tuple[
    GenTestOutcome, Optional[dict]
]:
    if outcome == BuildOutcome.NO_MAVEN:
        return GenTestOutcome.NO_MAVEN, None
    if outcome == BuildOutcome.COMPILE_FAILURE:
        # Original tests compiled in Phase 1; a new compile break is the
        # generated test's. No report is produced in this case.
        return GenTestOutcome.COMPILE_FAILURE, None
    if outcome == BuildOutcome.BUILD_ERROR:
        return GenTestOutcome.BUILD_ERROR, None

    # SUCCESS or TEST_FAILURE overall -> isolate the generated test itself.
    counts = _parse_generated_report(repo_dir, fqcn)
    if counts is None:
        return GenTestOutcome.NO_TESTS, None
    if counts["failures"] + counts["errors"] > 0:
        return GenTestOutcome.TEST_FAILURE, counts
    if counts["total"] - counts["skipped"] > 0:
        return GenTestOutcome.PASS, counts
    return GenTestOutcome.NO_TESTS, counts


def execute_generated_test(
    repo_dir: Union[str, Path],
    workspace: Workspace,
    generated_class: str,
    maven_extra_args: Optional[Sequence[str]] = None,
) -> GenExecResult:
    """Run the suite (incl. the generated test) and record the generated
    test's isolated outcome plus the after-coverage.

    ``generated_class`` is the fully-qualified name of the written test class,
    e.g. ``com.example.CalcAiGeneratedTest`` (see :func:`fqcn_of`).
    """
    repo_dir = Path(repo_dir)

    record, outcome = run_mvn_test_with_coverage(
        repo_dir, workspace, extra_args=maven_extra_args
    )
    gen_outcome, counts = _classify(repo_dir, generated_class, outcome)

    suite_result = parse_surefire(repo_dir)
    after_coverage = parse_jacoco(repo_dir).summary()
    gen_report_found = counts is not None
    counts = counts or {}

    return GenExecResult(
        generated_class=generated_class,
        gen_outcome=gen_outcome,
        build_outcome=outcome.value,
        gen_report_found=gen_report_found,
        gen_total=counts.get("total", 0),
        gen_passed=max(
            counts.get("total", 0)
            - counts.get("failures", 0)
            - counts.get("errors", 0)
            - counts.get("skipped", 0),
            0,
        ),
        gen_failed=counts.get("failures", 0),
        gen_errors=counts.get("errors", 0),
        gen_skipped=counts.get("skipped", 0),
        suite_result=suite_result.model_dump(),
        after_coverage=after_coverage,
        log_path=record.log_path if record else None,
        exec_record=record.trimmed() if record else None,
    )
