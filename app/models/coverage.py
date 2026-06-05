"""Structured JaCoCo coverage (P1-T08). Phase 1 captures the baseline only."""
from __future__ import annotations

from pydantic import BaseModel


def _rate(covered: int, missed: int) -> float:
    total = covered + missed
    return round(covered / total, 4) if total else 0.0


class Coverage(BaseModel):
    has_report: bool = False
    line_covered: int = 0
    line_missed: int = 0
    branch_covered: int = 0
    branch_missed: int = 0
    method_covered: int = 0
    method_missed: int = 0

    @property
    def line_rate(self) -> float:
        return _rate(self.line_covered, self.line_missed)

    @property
    def branch_rate(self) -> float:
        return _rate(self.branch_covered, self.branch_missed)

    @property
    def method_rate(self) -> float:
        return _rate(self.method_covered, self.method_missed)

    def summary(self) -> dict:
        """Serializable dict including computed rates (for reports/persistence)."""
        data = self.model_dump()
        data["line_rate"] = self.line_rate
        data["branch_rate"] = self.branch_rate
        data["method_rate"] = self.method_rate
        return data
