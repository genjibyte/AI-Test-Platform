"""submit_candidate tests (docs/53 S1). Offline; no Maven; no LLM.

Covers:
- run_kind: ``external`` is forced; caller cannot override; generator path cannot
  claim ``external`` (docs/53 §3, §4).
- state machine: the new SUBMIT_* transitions + the existing GEN_* path are intact.
- pipeline short-circuits (no DONE, no workspace, unresolvable target) yield
  ``SUBMIT_FAILED`` with the partial bundle preserved.
- result identity is platform-controlled: producer cannot set trusted=True, cannot
  rename the test class, cannot land outside src/test/java.
- the judge stack runs unchanged: ``assemble_generation_report`` over a submit
  bundle yields ``conclusion == NEED_HUMAN_REVIEW`` and ``trusted == False``.
- API validation: producer_id required / regex-checked / not 'fake-1'; test_source
  required / size-capped; missing job -> 404; un-judged job -> 409.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.submit_candidate import _MAX_TEST_SOURCE_BYTES, _PRODUCER_ID_RE
from app.config import Settings
from app.models.context_snapshot import ContextSnapshot, Target
from app.models.coverage import Coverage
from app.models.java_source import JavaClassStructure, JavaMethod, JavaParam
from app.llm.run_kind import (
    EXTERNAL_KIND,
    RUN_KINDS,
    resolve_run_kind,
    resolve_run_kind_for_submit,
)
from app.llm.schema import TestGenerationResult
from app.main import create_app
from app.models.job import Job, JobStatus, can_transition
from app.pipeline.submit_pipeline import (
    _result_for_submit,
    _submit_class_name,
    run_external_candidate,
)
from app.report.generation_report import CONCLUSION, assemble_generation_report
from app.runtime.workspace import Workspace
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo

SUBMIT_CHAIN = [
    JobStatus.TARGET_SELECT,
    JobStatus.CONTEXT,
    JobStatus.SUBMIT_EXECUTE,
    JobStatus.COMPARE,
]


@pytest.fixture()
def repo(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    return JobRepo(conn=get_connection(db))


# ---------- run_kind invariants -------------------------------------------------

def test_external_is_in_run_kinds():
    assert EXTERNAL_KIND == "external"
    assert EXTERNAL_KIND in RUN_KINDS
    assert set(RUN_KINDS) == {"real", "fake", "dryrun", "smoke", "external"}


def test_submit_run_kind_is_always_external():
    assert resolve_run_kind_for_submit() == "external"
    assert resolve_run_kind_for_submit("external") == "external"
    assert resolve_run_kind_for_submit("EXTERNAL") == "external"


@pytest.mark.parametrize("override", ["real", "fake", "dryrun", "smoke", "bogus"])
def test_submit_run_kind_rejects_any_non_external_override(override):
    with pytest.raises(ValueError):
        resolve_run_kind_for_submit(override)


def test_generator_path_cannot_claim_external():
    with pytest.raises(ValueError):
        resolve_run_kind(client_is_fake=False, override="external")
    with pytest.raises(ValueError):
        resolve_run_kind(client_is_fake=True, override="external")


# ---------- state machine -------------------------------------------------------

def test_submit_chain_transitions():
    assert can_transition(JobStatus.DONE, JobStatus.TARGET_SELECT)
    assert can_transition(JobStatus.TARGET_SELECT, JobStatus.CONTEXT)
    assert can_transition(JobStatus.CONTEXT, JobStatus.SUBMIT_EXECUTE)
    assert can_transition(JobStatus.SUBMIT_EXECUTE, JobStatus.COMPARE)
    assert can_transition(JobStatus.COMPARE, JobStatus.SUBMIT_DONE)


def test_submit_chain_can_fail():
    for s in SUBMIT_CHAIN:
        assert can_transition(s, JobStatus.SUBMIT_FAILED)


def test_submit_terminal_states_have_no_exit():
    assert not can_transition(JobStatus.SUBMIT_DONE, JobStatus.COMPARE)
    assert not can_transition(JobStatus.SUBMIT_DONE, JobStatus.SUBMIT_FAILED)
    assert not can_transition(JobStatus.SUBMIT_FAILED, JobStatus.TARGET_SELECT)


def test_generator_path_unaffected():
    assert can_transition(JobStatus.CONTEXT, JobStatus.GENERATE)
    assert can_transition(JobStatus.GENERATE, JobStatus.GEN_EXECUTE)
    assert can_transition(JobStatus.COMPARE, JobStatus.GEN_DONE)
    # cross-paths the state machine MUST NOT allow
    assert not can_transition(JobStatus.GENERATE, JobStatus.SUBMIT_EXECUTE)
    assert not can_transition(JobStatus.SUBMIT_EXECUTE, JobStatus.GENERATE)
    assert not can_transition(JobStatus.GEN_DONE, JobStatus.SUBMIT_DONE)


# ---------- pipeline short-circuits --------------------------------------------

_SRC = (
    "package com.example;\n"
    "class T { @org.junit.jupiter.api.Test void t(){} }\n"
)


def test_submit_requires_judged_job(repo):
    job = Job(git_url="https://example.com/x.git")  # status CREATED
    repo.create(job)
    out = run_external_candidate(
        job, repo, "com.example.Calc", "max", _SRC, producer_id="claude-4-7",
    )
    assert out.status == JobStatus.SUBMIT_FAILED
    assert "judged" in (out.error or "")
    assert out.generation and out.generation["error"]
    assert out.generation["run_kind"] == "external"


def test_submit_fails_when_workspace_missing(repo):
    job = Job(git_url="https://example.com/x.git", status=JobStatus.DONE)
    repo.create(job)
    out = run_external_candidate(
        job, repo, "com.example.Calc", "max", _SRC, producer_id="claude-4-7",
    )
    assert out.status == JobStatus.SUBMIT_FAILED
    assert "workspace" in (out.error or "")
    assert out.generation["producer_id"] == "claude-4-7"


def test_submit_pipeline_persists_asset_facts_before_preflight_reject(repo, tmp_path, monkeypatch):
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
    test_source = (
        "package org.apache.commons.lang3;\n"
        "class BooleanUtilsSubmittedTest {\n"
        "  void t() { BooleanUtils.toBooleanObject(1, 1, 0); }\n"
        "}\n"
    )

    monkeypatch.setattr(
        "app.pipeline.submit_pipeline.resolve_target",
        lambda *_args, **_kwargs: (target, structure),
    )
    monkeypatch.setattr(
        "app.pipeline.submit_pipeline.build_snapshot",
        lambda *_args, **_kwargs: snapshot,
    )
    monkeypatch.setattr(
        "app.pipeline.submit_pipeline.parse_jacoco",
        lambda *_args, **_kwargs: Coverage(),
    )
    monkeypatch.setattr(
        "app.pipeline.submit_pipeline.parse_jacoco_class",
        lambda *_args, **_kwargs: Coverage(),
    )

    out = run_external_candidate(
        job,
        repo,
        "org.apache.commons.lang3.BooleanUtils",
        None,
        test_source,
        producer_id="human:reviewer",
    )

    assert out.status == JobStatus.SUBMIT_DONE
    assert out.generation["execution"]["build_outcome"] == "PREFLIGHT_REJECT"
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


# ---------- platform-controlled result identity --------------------------------

def test_result_identity_is_platform_controlled():
    """The caller's test_source flows in verbatim; everything ELSE
    (target/class/file/trusted/producer_id) is set by us (docs/53 §2.1)."""
    r = _result_for_submit(
        target_class="com.example.Calc",
        target_method="max",
        package="com.example",
        test_source="// caller content\n",
        producer_id="claude-4-7",
    )
    assert r.target_class == "com.example.Calc"
    assert r.target_method == "max"
    assert r.test_class_name == "CalcSubmittedTest"  # not <Target>AiGeneratedTest
    assert r.file_name == "CalcSubmittedTest.java"
    assert r.trusted is False                        # HARD
    assert r.producer_id == "claude-4-7"
    assert r.model == "claude-4-7"                   # surfaces in analytics
    assert r.test_source == "// caller content\n"
    # creative caller-side fields are EMPTY (caller cannot self-certify)
    assert r.imports == [] and r.scenarios == [] and r.mocks == []


def test_submit_class_name_distinct_from_generator():
    """Submit and generator paths MUST land on disk in different files (docs/53 §1.1)."""
    assert _submit_class_name("com.example.Calc") == "CalcSubmittedTest"
    assert _submit_class_name("Calc") == "CalcSubmittedTest"
    assert "AiGenerated" not in _submit_class_name("com.example.Calc")


# ---------- judge stack runs UNCHANGED over a submit bundle --------------------

def test_assemble_generation_report_on_submit_bundle_holds_invariants():
    """The judge stack already accepts the bundle shape. For a submit run, it
    must still yield trusted=False, conclusion=NEED_HUMAN_REVIEW, and the digest."""
    bundle = {
        "target": {"target_class": "com.example.Calc", "target_method": "max"},
        "result": _result_for_submit(
            target_class="com.example.Calc",
            target_method="max",
            package="com.example",
            test_source="package com.example; class T {}",
            producer_id="claude-4-7",
        ).model_dump(),
        "write": {"created": True, "production_code_touched": False,
                  "content": "package com.example; class T {}"},
        "execution": {"gen_outcome": "PASS", "build_outcome": "SUCCESS",
                      "gen_total": 1, "gen_passed": 1, "gen_failed": 0,
                      "gen_errors": 0, "gen_skipped": 0},
        "error": None,
        "run_kind": "external",
        "producer_id": "claude-4-7",
        "producer_meta": {},
    }
    report = assemble_generation_report(bundle)
    assert report["conclusion"] == CONCLUSION == "NEED_HUMAN_REVIEW"
    assert report["trusted"] is False
    # the digest still emits the standing facts -- never accepts.
    dg = report["review_summary"]["digest"]
    assert dg["auto_accept_blocked"] is True
    assert dg["conclusion"] == "NEED_HUMAN_REVIEW"
    # Asset Gate is producer-agnostic: submitted candidates get the same advisory block.
    assert "asset_sufficiency" in report["review_summary"]
    assert report["review_summary"]["asset_sufficiency"]["advisory"] is True


# ---------- API validation -----------------------------------------------------

@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    """Stand up FastAPI with a temp DB; JobRepo() inside the endpoint gets the
    temp DB connection via Settings override."""
    monkeypatch.setenv("TESTAGENT_DB_PATH", str(tmp_path / "api.db"))
    # Make sure get_settings picks up the override.
    from app.config import get_settings
    get_settings.cache_clear()
    init_db(tmp_path / "api.db")
    app = create_app()
    return TestClient(app)


def _post(client, job_id, **overrides):
    body = {
        "target_class": "com.example.Calc",
        "target_method": "max",
        "test_source": _SRC,
        "producer_id": "claude-4-7",
    }
    body.update(overrides)
    return client.post(f"/jobs/{job_id}/submit_candidate", json=body)


def test_api_missing_producer_id(api_client):
    r = _post(api_client, "nope", producer_id="")
    assert r.status_code == 422


def test_api_invalid_producer_id_regex(api_client):
    r = _post(api_client, "nope", producer_id="bad space")
    assert r.status_code == 422


def test_api_reserved_producer_id_fake_one(api_client):
    """fake-1 is reserved for FakeLLMClient (docs/43). Cannot be impersonated."""
    r = _post(api_client, "nope", producer_id="fake-1")
    assert r.status_code == 422
    assert "reserved" in r.json()["detail"].lower()


def test_api_empty_test_source(api_client):
    r = _post(api_client, "nope", test_source="   \n")
    assert r.status_code == 422


def test_api_oversize_test_source(api_client):
    big = "x" * (_MAX_TEST_SOURCE_BYTES + 1)
    r = _post(api_client, "nope", test_source=big)
    assert r.status_code == 422


def test_api_job_not_found(api_client):
    r = _post(api_client, "does-not-exist")
    assert r.status_code == 404


def test_api_unjudged_job_returns_409(api_client):
    """A CREATED job cannot be submitted into (must be DONE)."""
    repo = JobRepo()
    job = Job(git_url="https://example.com/x.git")
    repo.create(job)
    r = _post(api_client, job.id)
    assert r.status_code == 409


# ---------- producer_id regex sanity (docs/53 §6) ------------------------------

@pytest.mark.parametrize(
    "pid,ok",
    [
        ("claude-4-7", True),
        ("codex-cli@2026-06-12", True),
        ("human:wenchao", True),
        ("deepseek/v2", True),
        ("model+nightly", True),
        ("", False),
        ("bad space", False),
        ("with;semi", False),
        ("a" * 129, False),
    ],
)
def test_producer_id_regex(pid, ok):
    assert bool(_PRODUCER_ID_RE.fullmatch(pid)) is ok
