"""JaCoCo XML report parsing (P1-T08).

Aggregates the report-level <counter> totals across all ``jacoco.xml`` reports
found under the repo (handles multi-module). Reads only the top-level counters,
which JaCoCo emits as the overall totals per report.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Union

from app.models.coverage import Coverage


def _add(counter: dict, root: ET.Element) -> None:
    # only direct <counter> children of <report> are the grand totals
    for c in root.findall("counter"):
        ctype = c.get("type", "")
        missed = int(c.get("missed", "0") or 0)
        covered = int(c.get("covered", "0") or 0)
        agg = counter.setdefault(ctype, [0, 0])
        agg[0] += missed
        agg[1] += covered


def parse_jacoco(repo_dir: Union[str, Path]) -> Coverage:
    repo_dir = Path(repo_dir)
    files = sorted(repo_dir.glob("**/jacoco.xml"))
    if not files:
        return Coverage(has_report=False)

    counters: dict[str, list[int]] = {}
    parsed_any = False
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        _add(counters, root)
        parsed_any = True

    if not parsed_any:
        return Coverage(has_report=False)

    return _to_coverage(counters)


def _to_coverage(counters: dict[str, list[int]]) -> Coverage:
    line = counters.get("LINE", [0, 0])
    branch = counters.get("BRANCH", [0, 0])
    method = counters.get("METHOD", [0, 0])
    return Coverage(
        has_report=True,
        line_missed=line[0],
        line_covered=line[1],
        branch_missed=branch[0],
        branch_covered=branch[1],
        method_missed=method[0],
        method_covered=method[1],
    )


def parse_jacoco_class(repo_dir: Union[str, Path], target_class: str) -> Coverage:
    """Aggregate the per-class counters for ONE fully-qualified class.

    JaCoCo names classes in VM notation (``com/example/Calc``). A class element's
    direct <counter> children are its class-level totals (method counters are
    nested one level deeper and are not picked up here). Returns
    ``has_report=False`` when the class is absent from every report.
    """
    repo_dir = Path(repo_dir)
    vm_name = target_class.replace(".", "/")
    counters: dict[str, list[int]] = {}
    found = False
    for path in sorted(repo_dir.glob("**/jacoco.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for cls in root.iter("class"):
            if cls.get("name") == vm_name:
                _add(counters, cls)
                found = True
    if not found:
        return Coverage(has_report=False)
    return _to_coverage(counters)
