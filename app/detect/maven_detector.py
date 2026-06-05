"""Maven project detection (P1-T05).

Read-only inspection of an imported repo: locates the root ``pom.xml``, extracts
the coordinates needed for judging, and classifies single vs multi-module. Does
NOT modify the pom.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Union

from app.models.maven_project import MavenProject

_JAVA_VERSION_KEYS = (
    "maven.compiler.release",
    "maven.compiler.source",
    "maven.compiler.target",
    "java.version",
)


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.rsplit("}", 1)[-1]
    return root


def _text(parent: Optional[ET.Element], tag: str) -> Optional[str]:
    if parent is None:
        return None
    child = parent.find(tag)
    return child.text.strip() if child is not None and child.text else None


def detect(repo_dir: Union[str, Path]) -> MavenProject:
    repo_dir = Path(repo_dir)
    pom = repo_dir / "pom.xml"
    if not pom.is_file():
        return MavenProject(is_maven=False, reason="no pom.xml at repo root")

    try:
        root = _strip_ns(ET.parse(pom).getroot())
    except ET.ParseError as exc:
        return MavenProject(
            is_maven=False, pom_path="pom.xml", reason=f"invalid pom.xml: {exc}"
        )

    parent = root.find("parent")
    group_id = _text(root, "groupId") or _text(parent, "groupId")
    version = _text(root, "version") or _text(parent, "version")
    artifact_id = _text(root, "artifactId")
    packaging = _text(root, "packaging") or "jar"

    # java version from <properties>
    java_version = None
    props = root.find("properties")
    if props is not None:
        for key in _JAVA_VERSION_KEYS:
            val = _text(props, key)
            if val:
                java_version = val
                break

    # modules
    modules: list[str] = []
    modules_el = root.find("modules")
    if modules_el is not None:
        modules = [m.text.strip() for m in modules_el.findall("module") if m.text]
    multi_module = bool(modules) or packaging == "pom"

    main_src = "src/main/java" if (repo_dir / "src/main/java").is_dir() else None
    test_src = "src/test/java" if (repo_dir / "src/test/java").is_dir() else None

    return MavenProject(
        is_maven=True,
        pom_path="pom.xml",
        group_id=group_id,
        artifact_id=artifact_id,
        version=version,
        packaging=packaging,
        java_version=java_version,
        multi_module=multi_module,
        modules=modules,
        main_src=main_src,
        test_src=test_src,
        reason="multi-module detected; Phase 1 executes root only"
        if multi_module
        else None,
    )
