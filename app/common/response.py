"""Unified API response envelope (P1-T01).

Every endpoint returns ``{code, message, data}``. ``code == 0`` means success.
"""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "ok") -> "ApiResponse":
        return cls(code=0, message=message, data=data)

    @classmethod
    def fail(cls, code: int, message: str, data: Any = None) -> "ApiResponse":
        return cls(code=code, message=message, data=data)
