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
from app.context.maven_deps import summarize_build_constraints, summarize_dependencies
from app.models.context_snapshot import ContextSnapshot, NeighborTestSummary
from app.targeting.target_selector import resolve_target


class ContextError(Exception):
    """Raised when required context cannot be collected (explicit failure)."""


def _neighbor_source_excerpt(source: str, limit: int = 1600) -> str:
    """Return a bounded neighbor-test excerpt that includes real test behavior.

    Apache-style test files often start with long license headers and import
    lists; a naive ``source[:N]`` can miss every ``@Test`` method. Keep a compact
    import/style prelude, then splice in the first actual test body area.
    """
    if len(source) <= limit:
        return source

    test_idx = source.find("@Test")
    if test_idx == -1:
        return source[:limit]

    imports = [
        line for line in source.splitlines()
        if line.strip().startswith("import ")
    ]
    prelude = "\n".join(imports[:20]).strip()
    if prelude:
        prelude += "\n...\n"

    remaining = max(0, limit - len(prelude))
    return prelude + source[test_idx:test_idx + remaining]


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
                # Bounded excerpt so the generator can mirror assertion/mock
                # style (docs/07 §4.3) without dumping the file.
                source_excerpt=_neighbor_source_excerpt(source),
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
    constraints = summarize_build_constraints(repo_dir)

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
        build_constraints=constraints,
    )
