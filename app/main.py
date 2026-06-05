"""Application entrypoint (P1-T01).

Phase 1 scope: 判卷场 (the judging arena). NO LLM, NO test generation,
NO fixer, NO complex frontend. See docs/05_PHASE1_BACKLOG.md.

Run locally::

    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api import context, health, jobs, report
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
    return app


app = create_app()
