"""Health check endpoint (P1-T01)."""
from __future__ import annotations

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> ApiResponse:
    settings = get_settings()
    return ApiResponse.ok(
        data={
            "status": "up",
            "app": settings.app_name,
            "version": settings.app_version,
        }
    )
