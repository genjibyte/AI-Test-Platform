"""Standalone Phase 1 judge runner (P1-T11 deliverable).

Runs the full judging pipeline over a git repo and prints the assembled report
as JSON. Useful for end-to-end validation against a real open-source Maven
project on a host where Maven is available.

Usage::

    set TESTAGENT_MAVEN_CMD=C:\\path\\to\\mvn.cmd   # if mvn not on PATH
    python -m scripts.run_judge https://github.com/<org>/<repo>.git [branch]
"""
from __future__ import annotations

import json
import sys

from app.config import get_settings
from app.models.job import Job
from app.pipeline.judge_pipeline import run_pipeline
from app.report.report_assembler import assemble_report
from app.storage.db import get_connection, init_db
from app.storage.job_repo import JobRepo


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m scripts.run_judge <git_url> [branch]")
        return 2
    git_url = argv[1]
    branch = argv[2] if len(argv) > 2 else None

    settings = get_settings()
    settings.ensure_dirs()
    init_db()

    repo = JobRepo(conn=get_connection())
    job = Job(git_url=git_url, branch=branch)
    repo.create(job)
    job = run_pipeline(job, repo)

    print(json.dumps(assemble_report(job), indent=2, ensure_ascii=False))
    return 0 if job.status.value == "DONE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
