"""Coverage delta between the Phase 1 baseline and the after-generation run (P2-T08).

Records overall and target-class line/branch coverage before vs after, plus two
explicit judgements that matter to the Charter north-star metrics:

- ``coverage_dropped``  -> overall coverage must NOT drop (Charter §6 item 4);
- ``target_improved``   -> target class coverage should rise (Charter §6 item 5).

These are FACTS, not a verdict. Accept/reject stays in Phase 4.
"""
from __future__ import annotations

from pydantic import BaseModel

# Rates are rounded to 4 dp by the Coverage model; use a matching epsilon so
# floating-point noise never flips a flag.
EPS = 1e-9


class CoverageDelta(BaseModel):
    target_class: str

    # Coverage.summary() dicts (include line_rate / branch_rate / method_rate).
    overall_before: dict
    overall_after: dict
    target_before: dict
    target_after: dict

    # Rate deltas (after - before), rounded to 4 dp.
    overall_line_delta: float
    overall_branch_delta: float
    target_line_delta: float
    target_branch_delta: float

    coverage_dropped: bool   # overall line OR branch rate decreased
    target_improved: bool    # target line OR branch rate increased
