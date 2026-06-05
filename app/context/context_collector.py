"""Bounded Context Snapshot builder (P2-T01).

Assembles ONLY the docs/07 §P4 bounded context for a target. Fails explicitly
when required context (class / method) is missing — never invents anything, and
never reads the whole repository into the snapshot.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from app.context.class_index import list_classes
from app.context.java_parser import extract_test_methods, parse_java
from app.context.maven_deps import summarize_dependencies
from app.models.context_snapshot import ContextSnapshot, NeighborTestSummary
from app.targeting.target_selector import resolve_target


class ContextError(Exception):
    """Raised when required context cannot be collected (explicit failure)."""


def _find_neighbor_test(
    repo_dir: Path, package: Optional[str], simple_name: str
) -> NeighborTestSummary:
    candidates = {f"{simple_name}Test", f"{simple_name}Tests", f"Test{simple_name}"}
    for ref in list_classes(repo_dir, kind="test"):
        if ref.simple_name in candidates and (package is None or ref.package == package):
            path = repo_dir / ref.file_path
            source = path.read_text(encoding="utf-8", errors="replace")
            structure = parse_java(source)
            return NeighborTestSummary(
                found=True,
                file_path=ref.file_path,
                class_name=structure.class_name if structure else ref.simple_name,
                test_methods=extract_test_methods(source),
            )
    return NeighborTestSummary(found=False)


def build_snapshot(
    repo_dir: Union[str, Path],
    target_class: str,
    target_method: Optional[str] = None,
) -> ContextSnapshot:
    repo_dir = Path(repo_dir)
    target, structure = resolve_target(repo_dir, target_class, target_method)
    if not target.exists or structure is None:
        raise ContextError(target.reason or "target class not found")
    if target_method is not None and target.method_exists is False:
        raise ContextError(
            f"target method '{target_method}' not found in {target_class}"
        )

    method_source: Optional[str] = None
    if target_method is not None:
        for m in structure.methods:
            if m.name == target_method:
                method_source = m.source
                break

    neighbor = _find_neighbor_test(repo_dir, structure.package, structure.class_name)
    deps = summarize_dependencies(repo_dir)

    return ContextSnapshot(
        target_class=target_class,
        target_method=target_method,
        target_method_source=method_source,
        class_structure=structure,
        imports=structure.imports,
        constructors=structure.constructors,
        fields=structure.fields,
        neighbor_test=neighbor,
        maven_dependencies=deps,
    )
