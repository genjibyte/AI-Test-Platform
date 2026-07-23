"""Application entrypoint.

The app exposes the current judge/report API surface. See docs/WORK_LOG.md and
docs/README.md for the active architecture map and routed documentation index.

Run locally::

    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api import context, generation, health, jobs, report, submit_candidate
from app.config import get_settings
from app.storage.db import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_dirs()
    init_db()

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(report.router)
    app.include_router(context.router)
    app.include_router(generation.router)
    app.include_router(submit_candidate.router)
    return app


app = create_app()
