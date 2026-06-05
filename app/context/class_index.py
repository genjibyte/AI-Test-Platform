"""Class listing / lookup over an imported Maven project (P2-T01).

Lists Java classes under ``src/main/java`` source roots (multi-module aware) and
resolves a fully-qualified class name to its source file. Read-only.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel


class ClassRef(BaseModel):
    fqn: str
    simple_name: str
    package: Optional[str] = None
    file_path: str  # relative to repo root


def find_source_roots(repo_dir: Union[str, Path], kind: str = "main") -> List[Path]:
    repo_dir = Path(repo_dir)
    pattern = f"**/src/{kind}/java"
    roots = [p for p in repo_dir.glob(pattern) if p.is_dir()]
    return sorted(roots)


def list_classes(repo_dir: Union[str, Path], kind: str = "main") -> List[ClassRef]:
    repo_dir = Path(repo_dir)
    refs: List[ClassRef] = []
    for root in find_source_roots(repo_dir, kind):
        for java in sorted(root.rglob("*.java")):
            if java.name == "package-info.java":
                continue
            rel_to_root = java.relative_to(root)
            package = ".".join(rel_to_root.parent.parts) or None
            simple = java.stem
            fqn = f"{package}.{simple}" if package else simple
            refs.append(
                ClassRef(
                    fqn=fqn,
                    simple_name=simple,
                    package=package,
                    file_path=str(java.relative_to(repo_dir)).replace("\\", "/"),
                )
            )
    return refs


def find_class_file(
    repo_dir: Union[str, Path], fqn: str, kind: str = "main"
) -> Optional[Path]:
    for ref in list_classes(repo_dir, kind):
        if ref.fqn == fqn:
            return Path(repo_dir) / ref.file_path
    return None
