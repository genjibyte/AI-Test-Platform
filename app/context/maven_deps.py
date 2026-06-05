"""Maven dependency summary (P2-T01). Read-only pom parsing."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Union

from app.detect.maven_detector import _strip_ns, _text
from app.models.context_snapshot import DependencySummary


def summarize_dependencies(repo_dir: Union[str, Path]) -> List[DependencySummary]:
    pom = Path(repo_dir) / "pom.xml"
    if not pom.is_file():
        return []
    try:
        root = _strip_ns(ET.parse(pom).getroot())
    except ET.ParseError:
        return []

    deps_el = root.find("dependencies")
    if deps_el is None:
        return []

    out: List[DependencySummary] = []
    for dep in deps_el.findall("dependency"):
        group = _text(dep, "groupId")
        artifact = _text(dep, "artifactId")
        if not group or not artifact:
            continue
        out.append(
            DependencySummary(
                group_id=group,
                artifact_id=artifact,
                version=_text(dep, "version"),
                scope=_text(dep, "scope"),
            )
        )
    return out
