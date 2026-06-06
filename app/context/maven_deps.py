"""Maven dependency summary (P2-T01). Read-only pom parsing."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Union

from app.detect.maven_detector import _strip_ns, _text
from app.models.context_snapshot import BuildConstraints, DependencySummary


def _properties(root) -> dict[str, str]:
    props = root.find("properties")
    if props is None:
        return {}
    return {
        child.tag: (child.text or "").strip()
        for child in list(props)
        if child.tag and child.text
    }


def _resolve(value: Optional[str], props: dict[str, str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if value.startswith("${") and value.endswith("}"):
        return props.get(value[2:-1], value)
    return value


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


def summarize_build_constraints(repo_dir: Union[str, Path]) -> BuildConstraints:
    pom = Path(repo_dir) / "pom.xml"
    if not pom.is_file():
        return BuildConstraints()
    try:
        root = _strip_ns(ET.parse(pom).getroot())
    except ET.ParseError:
        return BuildConstraints()

    props = _properties(root)
    return BuildConstraints(
        java_source=_resolve(props.get("maven.compiler.source"), props),
        java_target=_resolve(props.get("maven.compiler.target"), props),
        java_release=_resolve(props.get("maven.compiler.release"), props),
    )
