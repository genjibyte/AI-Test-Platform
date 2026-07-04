"""Tests for the Phase 2 generation pipeline + state machine (P2-T10).

Maven-free: covers the state-machine wiring and the GEN_FAILED short-circuits.
The real happy path (mvn execute + coverage) is the Phase 2 e2e (P2-T11).
"""
import pytest

from app.config import Settings
from app.llm.schema import TestGenerationResult
from app.models.context_snapshot import ContextSnapshot, Target
from app.models.coverage import Coverage
from app.models.job import Job, JobStatus, can_transition
from app.models.java_source import JavaClassStructure, JavaMethod, JavaParam
from app.pipeline.generate_pipeline import run_generation
from app.report.generation_report import assemble_generation_report
from app.runtime.workspace import Workspace
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo

P2_CHAIN = [
    JobStatus.TARGET_SELECT,
    JobStatus.CONTEXT,
    JobStatus.GENERATE,
    JobStatus.GEN_EXECUTE,
    JobStatus.COMPARE,
]


@pytest.fixture()
def repo(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    return JobRepo(conn=get_connection(db))


def test_phase2_forward_transitions_allowed():
    assert can_transition(JobStatus.DONE, JobStatus.TARGET_SELECT)
    assert can_transition(JobStatus.TARGET_SELECT, JobStatus.CONTEXT)
    assert can_transition(JobStatus.CONTEXT, JobStatus.GENERATE)
    assert can_transition(JobStatus.GENERATE, JobStatus.GEN_EXECUTE)
    assert can_transition(JobStatus.GEN_EXECUTE, JobStatus.COMPARE)
    assert can_transition(JobStatus.COMPARE, JobStatus.GEN_DONE)


def test_every_phase2_step_can_fail():
    for s in P2_CHAIN:
        assert can_transition(s, JobStatus.GEN_FAILED)


def test_terminal_states_have_no_exit():
    assert not can_transition(JobStatus.GEN_DONE, JobStatus.GEN_FAILED)
    assert not can_transition(JobStatus.GEN_FAILED, JobStatus.TARGET_SELECT)


def test_done_cannot_skip_target_select():
    # DONE must enter via TARGET_SELECT, not jump straight to GENERATE.
    assert not can_transition(JobStatus.DONE, JobStatus.GENERATE)


def test_phase1_unaffected():
    assert can_transition(JobStatus.CREATED, JobStatus.IMPORTING)
    assert not can_transition(JobStatus.CREATED, JobStatus.DONE)


def test_generation_requires_judged_job(repo):
    job = Job(git_url="https://example.com/x.git")  # status CREATED
    repo.create(job)
    out = run_generation(job, repo, "com.example.Calc", "max")
    assert out.status == JobStatus.GEN_FAILED
    assert "judged" in (out.error or "")
    assert out.generation and out.generation["error"]


def test_generation_fails_when_workspace_missing(repo):
    # A judged job whose workspace no longer exists on disk.
    job = Job(git_url="https://example.com/x.git", status=JobStatus.DONE)
    repo.create(job)
    out = run_generation(job, repo, "com.example.Calc", "max")
    assert out.status == JobStatus.GEN_FAILED
    assert "workspace" in (out.error or "")


def test_preflight_rejects_before_write_and_maven(repo, tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "ws", data_dir=tmp_path / "data")
    monkeypatch.setattr("app.runtime.workspace.get_settings", lambda: settings)

    job = Job(git_url="https://example.com/x.git", status=JobStatus.DONE)
    repo.create(job)
    ws = Workspace(job.id).create()
    ws.repo_dir.mkdir(parents=True, exist_ok=True)

    structure = JavaClassStructure(
        package="org.apache.commons.lang3",
        class_name="BooleanUtils",
        methods=[
            JavaMethod(
                return_type="Boolean",
                name="toBooleanObject",
                params=[JavaParam(type="int", name="value")],
                signature="public static Boolean toBooleanObject",
                source="",
            ),
            JavaMethod(
                return_type="Boolean",
                name="toBooleanObject",
                params=[
                    JavaParam(type="int", name="value"),
                    JavaParam(type="int", name="trueValue"),
                    JavaParam(type="int", name="falseValue"),
                    JavaParam(type="int", name="nullValue"),
                ],
                signature="public static Boolean toBooleanObject",
                source="",
            ),
        ],
    )
    snapshot = ContextSnapshot(
        target_class="org.apache.commons.lang3.BooleanUtils",
        class_structure=structure,
    )
    target = Target(
        target_class="org.apache.commons.lang3.BooleanUtils",
        file_path="src/main/java/org/apache/commons/lang3/BooleanUtils.java",
        exists=True,
    )
    result = TestGenerationResult(
        target_class="org.apache.commons.lang3.BooleanUtils",
        package="org.apache.commons.lang3",
        test_class_name="BooleanUtilsAiGeneratedTest",
        file_name="BooleanUtilsAiGeneratedTest.java",
        test_source=(
            "package org.apache.commons.lang3;\n"
            "class BooleanUtilsAiGeneratedTest {\n"
            "  void t() { BooleanUtils.toBooleanObject(1, 1, 0); }\n"
            "}\n"
        ),
        model="fixture",
    )

    called = {"write": False, "execute": False}
    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.resolve_target",
        lambda *_args, **_kwargs: (target, structure),
    )
    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.build_snapshot",
        lambda *_args, **_kwargs: snapshot,
    )
    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.parse_jacoco",
        lambda *_args, **_kwargs: Coverage(),
    )
    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.parse_jacoco_class",
        lambda *_args, **_kwargs: Coverage(),
    )
    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.dry_generate",
        lambda *_args, **_kwargs: result,
    )

    def _write_should_not_run(*_args, **_kwargs):
        called["write"] = True
        raise AssertionError("write_generated_test should not run")

    def _execute_should_not_run(*_args, **_kwargs):
        called["execute"] = True
        raise AssertionError("execute_generated_test should not run")

    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.write_generated_test",
        _write_should_not_run,
    )
    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.execute_generated_test",
        _execute_should_not_run,
    )

    out = run_generation(
        job, repo, "org.apache.commons.lang3.BooleanUtils", client=object()
    )

    assert out.status == JobStatus.GEN_DONE
    assert called == {"write": False, "execute": False}
    assert out.generation["write"] is None
    assert out.generation["execution"]["gen_outcome"] == "COMPILE_FAILURE"
    assert out.generation["execution"]["build_outcome"] == "PREFLIGHT_REJECT"
    assert out.generation["preflight"]["status"] == "FAIL"
    assert out.generation["asset_facts"] == {
        "neighbor_test_found": False,
        "neighbor_test_methods": 0,
        "dependency_artifacts": [],
        "build_java_source": None,
        "target_has_method_source": False,
        "target_method_specified": False,
        "target_fields": 0,
        "target_constructors": 0,
        "target_methods": 2,
    }

    report = assemble_generation_report(out.generation)
    assert report["compiled"] is False
    assert report["preflight"]["blocking_issues"][0]["code"] == (
        "unlisted_target_overload_arity"
    )
    assert report["review_summary"]["preflight"]["blockers"][0]["code"] == (
        "unlisted_target_overload_arity"
    )


def test_repair_safety_stop_discards_oracle_touching_repair(repo, tmp_path, monkeypatch):
    """A repair that altered the oracle skeleton is discarded by the pipeline:
    not written to disk, Maven not re-run, safety_stop recorded (docs/38)."""
    import types

    from app.generate.gen_executor import GenTestOutcome  # noqa: F401
    from app.generate.test_writer import WriteResult
    from app.pipeline.generate_pipeline import _preflight_reject_result
    from app.repair.compile_repair import CompileRepairResult

    settings = Settings(workspace_root=tmp_path / "ws", data_dir=tmp_path / "data")
    monkeypatch.setattr("app.runtime.workspace.get_settings", lambda: settings)

    job = Job(git_url="https://example.com/x.git", status=JobStatus.DONE)
    repo.create(job)
    ws = Workspace(job.id).create()
    ws.repo_dir.mkdir(parents=True, exist_ok=True)

    structure = JavaClassStructure(package="com.example", class_name="Calc", methods=[])
    snapshot = ContextSnapshot(
        target_class="com.example.Calc", class_structure=structure
    )
    target = Target(
        target_class="com.example.Calc",
        file_path="src/main/java/com/example/Calc.java",
        exists=True,
    )
    result = TestGenerationResult(
        target_class="com.example.Calc",
        package="com.example",
        test_class_name="CalcAiGeneratedTest",
        file_name="CalcAiGeneratedTest.java",
        test_source="package com.example;\nclass CalcAiGeneratedTest { }\n",
        model="fixture",
    )

    rel = "src/test/java/com/example/CalcAiGeneratedTest.java"
    original = (
        "package com.example;\n"
        "class CalcAiGeneratedTest {\n"
        "  void t() { assertEquals(2, Calc.add(1, 1)); }\n"
        "}\n"
    )
    abs_path = ws.repo_dir / rel
    # malicious "repair": rewrites the expected value -> oracle NOT preserved.
    malicious = original.replace("assertEquals(2,", "assertEquals(999,")

    def _fake_write(repo_dir, res, *a, **k):
        p = repo_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(original, encoding="utf-8")
        return WriteResult(file_path=rel, test_class_name=res.test_class_name,
                           created=True, content=original)

    exec_calls = {"n": 0}

    def _fake_exec(*a, **k):
        exec_calls["n"] += 1
        return _preflight_reject_result("com.example.CalcAiGeneratedTest")  # COMPILE_FAILURE

    def _fake_repair(source, log_text="", java_source_level=None):
        return CompileRepairResult(
            changed=True, source=malicious, patches=[], oracle_preserved=False
        )

    monkeypatch.setattr("app.pipeline.generate_pipeline.resolve_target",
                        lambda *a, **k: (target, structure))
    monkeypatch.setattr("app.pipeline.generate_pipeline.build_snapshot",
                        lambda *a, **k: snapshot)
    monkeypatch.setattr("app.pipeline.generate_pipeline.parse_jacoco",
                        lambda *a, **k: Coverage())
    monkeypatch.setattr("app.pipeline.generate_pipeline.parse_jacoco_class",
                        lambda *a, **k: Coverage())
    monkeypatch.setattr("app.pipeline.generate_pipeline.dry_generate",
                        lambda *a, **k: result)
    monkeypatch.setattr(
        "app.pipeline.generate_pipeline.evaluate_generated_test_preflight",
        lambda *a, **k: types.SimpleNamespace(
            status="PASS", model_dump=lambda: {"status": "PASS"}),
    )
    monkeypatch.setattr("app.pipeline.generate_pipeline.write_generated_test",
                        _fake_write)
    monkeypatch.setattr("app.pipeline.generate_pipeline.execute_generated_test",
                        _fake_exec)
    monkeypatch.setattr("app.pipeline.generate_pipeline.repair_compile_failure",
                        _fake_repair)

    out = run_generation(
        job, repo, "com.example.Calc", client=object(),
        repair_compile_failures=True, max_repair_rounds=1,
    )

    assert out.status == JobStatus.GEN_DONE
    # the oracle-touching repair was discarded: on-disk file keeps the original oracle.
    assert abs_path.read_text(encoding="utf-8") == original
    assert "assertEquals(999" not in abs_path.read_text(encoding="utf-8")
    rep = out.generation["repair"]
    assert rep["safety_stopped"] is True
    assert rep["repair_rounds"] == 0                 # reverted round does not count
    last = rep["rounds"][-1]
    assert last["safety_stop"] == "oracle_signature_changed"
    assert last["oracle_preserved"] is False
    # Maven ran once (initial); the post-repair re-run was skipped by the safety stop.
    assert exec_calls["n"] == 1
