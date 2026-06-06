"""Phase 2 end-to-end with REAL Maven (P2-T11).

Gated on ``TESTAGENT_E2E=1``. Drives the whole Phase 2 chain on the committed
``samples/calc`` fixture using a deterministic offline fixture client (no real
LLM): judged baseline -> target -> context -> generate -> write -> execute ->
coverage compare -> report.

Two cases, deliberately covering success AND failure (docs/07 A4 — never only
demo success):

1. ``test_phase2_success`` — a real generated test that exercises ``max``'s
   uncovered branch: compiles, runs green, raises target branch coverage, and
   does NOT touch production code or the existing test.
2. ``test_phase2_compile_failure_surfaced`` — a generated test referencing a
   non-existent method: the pipeline still completes (GEN_DONE) and the report
   truthfully reports ``compiled=False`` with ``NEED_HUMAN_REVIEW`` — the
   failure is surfaced, not hidden.

Run::

    set TESTAGENT_MAVEN_CMD=...\\mvn.cmd
    set TESTAGENT_E2E=1
    pytest tests/e2e/test_phase2_e2e.py -v -s
"""
import json
import os
from pathlib import Path

import pytest

from app.build.maven_runner import resolve_maven
from app.config import Settings
from app.coverage.jacoco_parser import parse_jacoco
from app.coverage.jacoco_runner import run_mvn_test_with_coverage
from app.llm.client import LLMClient, LLMResponse
from app.models.job import Job, JobStatus
from app.pipeline.generate_pipeline import run_generation
from app.report.generation_report import assemble_generation_report
from app.runtime.workspace import Workspace
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo

pytestmark = pytest.mark.skipif(
    os.environ.get("TESTAGENT_E2E") != "1", reason="set TESTAGENT_E2E=1 to run"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "samples" / "calc"

# Covers max's UNCOVERED false branch (baseline CalcTest only does max(7,3)).
SUCCESS_SRC = (
    "import org.junit.jupiter.api.Test;\n"
    "import static org.junit.jupiter.api.Assertions.assertEquals;\n\n"
    "class CalcAiGeneratedTest {\n"
    "    @Test void maxFirstBigger() { assertEquals(5, new Calc().max(5, 3)); }\n"
    "    @Test void maxSecondBigger() { assertEquals(9, new Calc().max(2, 9)); }\n"
    "}\n"
)

# References Calc.multiply(...) which does not exist -> compile failure.
BOGUS_SRC = (
    "import org.junit.jupiter.api.Test;\n"
    "import static org.junit.jupiter.api.Assertions.assertEquals;\n\n"
    "class CalcAiGeneratedTest {\n"
    "    @Test void bogus() { assertEquals(1, new Calc().multiply(1, 1)); }\n"
    "}\n"
)


class _FixtureClient(LLMClient):
    """Deterministic offline client returning a fixed test_source."""

    def __init__(self, test_source: str):
        self._src = test_source

    def generate(self, prompt: str) -> LLMResponse:
        payload = {
            "imports": [],
            "test_source": self._src,
            "scenarios": ["max: first bigger", "max: second bigger"],
            "mocks": [],
        }
        return LLMResponse(
            text=json.dumps(payload), provider="fixture", model="fixture-1"
        )


def _copy_sources(dst: Path) -> None:
    """Copy the fixture WITHOUT its stale target/ build output."""
    for path in SAMPLE.rglob("*"):
        if path.is_dir() or "target" in path.relative_to(SAMPLE).parts:
            continue
        out = dst / path.relative_to(SAMPLE)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(path.read_bytes())


def _judged_job(tmp_path, monkeypatch) -> tuple[Job, JobRepo]:
    """Build a DONE job whose workspace holds calc + a real baseline coverage."""
    if resolve_maven(SAMPLE) is None:
        pytest.skip("maven not resolvable (set TESTAGENT_MAVEN_CMD)")

    settings = Settings(
        workspace_root=tmp_path / "ws",
        data_dir=tmp_path / "data",
        maven_cmd=os.environ.get("TESTAGENT_MAVEN_CMD"),
    )
    monkeypatch.setattr("app.runtime.workspace.get_settings", lambda: settings)

    db = tmp_path / "e2e.db"
    init_db(db)
    repo = JobRepo(conn=get_connection(db))
    job = Job(git_url="file://local-fixture")
    repo.create(job)

    ws = Workspace(job.id).create()
    _copy_sources(ws.repo_dir)

    record, outcome = run_mvn_test_with_coverage(ws.repo_dir, ws)
    assert outcome.value == "SUCCESS", (record.stdout or "")[-2000:]
    job.coverage = parse_jacoco(ws.repo_dir).summary()
    job.build_outcome = "SUCCESS"
    job.status = JobStatus.DONE
    repo.save(job)
    return job, repo


def _assert_prod_untouched(job_id: str):
    repo_dir = Workspace(job_id).repo_dir
    calc = (repo_dir / "src/main/java/com/example/Calc.java").read_text("utf-8")
    calc_test = (repo_dir / "src/test/java/com/example/CalcTest.java").read_text("utf-8")
    assert "public class Calc" in calc and "multiply" not in calc
    assert "class CalcTest" in calc_test  # existing test untouched


def test_phase2_success(tmp_path, monkeypatch):
    job, repo = _judged_job(tmp_path, monkeypatch)
    out = run_generation(
        job, repo, "com.example.Calc", "max", client=_FixtureClient(SUCCESS_SRC)
    )
    assert out.status == JobStatus.GEN_DONE, out.error

    report = assemble_generation_report(out.generation)
    assert report["compiled"] and report["executed"] and report["passed"]
    assert report["gen_counts"]["passed"] == 2 and report["gen_counts"]["failed"] == 0

    cd = report["coverage_delta"]
    assert cd["coverage_dropped"] is False
    assert cd["target_improved"] is True
    assert cd["target_branch_delta"] > 0

    assert report["production_code_touched"] is False
    assert report["trusted"] is False
    assert report["conclusion"] == "NEED_HUMAN_REVIEW"
    assert report["test_file"].endswith("CalcAiGeneratedTest.java")
    _assert_prod_untouched(out.id)


def test_phase2_compile_failure_surfaced(tmp_path, monkeypatch):
    job, repo = _judged_job(tmp_path, monkeypatch)
    out = run_generation(
        job, repo, "com.example.Calc", "max", client=_FixtureClient(BOGUS_SRC)
    )
    # Pipeline COMPLETES (records the result); it does not crash or hide it.
    assert out.status == JobStatus.GEN_DONE, out.error

    report = assemble_generation_report(out.generation)
    assert report["gen_outcome"] == "COMPILE_FAILURE"
    assert report["compiled"] is False
    assert report["executed"] is False
    assert report["passed"] is False
    assert report["conclusion"] == "NEED_HUMAN_REVIEW"
    _assert_prod_untouched(out.id)
