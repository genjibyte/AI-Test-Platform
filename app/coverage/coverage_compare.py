"""Compare baseline vs after-generation coverage (P2-T08).

Pure computation over two pairs of :class:`Coverage` snapshots (overall and the
target class). No Maven, no I/O — the snapshots are produced by ``parse_jacoco``
/ ``parse_jacoco_class`` (baseline from the Phase 1 job, after from P2-T07).
"""
from __future__ import annotations

from app.models.coverage import Coverage
from app.models.coverage_delta import EPS, CoverageDelta


def _delta(after: float, before: float) -> float:
    return round(after - before, 4)


def compare(
    overall_before: Coverage,
    overall_after: Coverage,
    target_before: Coverage,
    target_after: Coverage,
    target_class: str,
) -> CoverageDelta:
    overall_line = _delta(overall_after.line_rate, overall_before.line_rate)
    overall_branch = _delta(overall_after.branch_rate, overall_before.branch_rate)
    target_line = _delta(target_after.line_rate, target_before.line_rate)
    target_branch = _delta(target_after.branch_rate, target_before.branch_rate)

    return CoverageDelta(
        target_class=target_class,
        overall_before=overall_before.summary(),
        overall_after=overall_after.summary(),
        target_before=target_before.summary(),
        target_after=target_after.summary(),
        overall_line_delta=overall_line,
        overall_branch_delta=overall_branch,
        target_line_delta=target_line,
        target_branch_delta=target_branch,
        coverage_dropped=overall_line < -EPS or overall_branch < -EPS,
        target_improved=target_line > EPS or target_branch > EPS,
    )
