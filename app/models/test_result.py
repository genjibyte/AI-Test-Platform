"""Structured Surefire test results (P1-T07)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class FailedCase(BaseModel):
    classname: str
    name: str
    type: str          # "failure" (assertion) or "error" (exception)
    message: str = ""


class TestResult(BaseModel):
    has_reports: bool = False
    suites: int = 0
    total: int = 0
    passed: int = 0
    failed: int = 0     # assertion failures
    errors: int = 0     # unexpected exceptions
    skipped: int = 0
    failed_cases: List[FailedCase] = Field(default_factory=list)

    @property
    def green(self) -> bool:
        return self.has_reports and self.failed == 0 and self.errors == 0
