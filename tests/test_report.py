"""Tests for report assembly + endpoints (P1-T10)."""
from fastapi.testclient import TestClient

from app.main import app
from app.models.job import Job, JobStatus
from app.report.report_assembler import assemble_report

client = TestClient(app)


def _done_job() -> Job:
    return Job(
        git_url="https://example.com/x.git",
        commit_sha="abc123",
        status=JobStatus.DONE,
        build_outcome="SUCCESS",
        project={"is_maven": True, "artifact_id": "demo"},
        test_result={"has_reports": True, "total": 3, "passed": 3,
                     "failed": 0, "errors": 0},
        coverage={"has_report": True, "line_rate": 0.9},
        stages=[
            {"name": "import", "exit_code": 0, "duration_ms": 100,
             "timed_out": False, "log_path": "/tmp/import.log"},
            {"name": "mvn-test-jacoco", "exit_code": 0, "duration_ms": 5000,
             "timed_out": False, "log_path": "/tmp/mvn.log"},
        ],
    )


def test_assemble_report_done():
    report = assemble_report(_done_job())
    assert report["status"] == "DONE"
    assert report["buildable"] is True
    assert report["tests_green"] is True
    assert report["coverage"]["line_rate"] == 0.9
    assert len(report["stages"]) == 2
    assert report["stages"][0]["log"].endswith("/logs/import")


def test_assemble_report_test_failure_buildable_but_not_green():
    job = _done_job()
    job.build_outcome = "TEST_FAILURE"
    job.test_result = {"has_reports": True, "total": 3, "passed": 2,
                       "failed": 1, "errors": 0}
    report = assemble_report(job)
    assert report["buildable"] is True
    assert report["tests_green"] is False


def test_report_404_for_missing_job():
    resp = client.get("/jobs/does-not-exist/report")
    assert resp.status_code == 404


def test_log_404_for_missing_job():
    resp = client.get("/jobs/does-not-exist/logs/import")
    assert resp.status_code == 404
