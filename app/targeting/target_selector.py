"""Target class/method resolution + validation (P2-T01).

Locates a user-specified class (and optional method) in the imported repo and
validates existence. Read-only; no generation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

from app.context.class_index import find_class_file
from app.context.java_parser import parse_java
from app.models.context_snapshot import Target
from app.models.java_source import JavaClassStructure


def resolve_target(
    repo_dir: Union[str, Path],
    target_class: str,
    target_method: Optional[str] = None,
) -> Tuple[Target, Optional[JavaClassStructure]]:
    path = find_class_file(repo_dir, target_class)
    if path is None or not path.is_file():
        return (
            Target(
                target_class=target_class,
                target_method=target_method,
                exists=False,
                reason="class not found under src/main/java",
            ),
            None,
        )

    rel = str(path.relative_to(Path(repo_dir))).replace("\\", "/")
    source = path.read_text(encoding="utf-8", errors="replace")
    structure = parse_java(source, file_path=rel)
    if structure is None:
        return (
            Target(
                target_class=target_class,
                target_method=target_method,
                file_path=rel,
                exists=False,
                reason="could not parse a primary type from source",
            ),
            None,
        )

    method_exists: Optional[bool] = None
    if target_method is not None:
        names = {m.name for m in structure.methods}
        method_exists = target_method in names

    target = Target(
        target_class=target_class,
        target_method=target_method,
        file_path=rel,
        exists=True,
        method_exists=method_exists,
        reason=None if (method_exists is None or method_exists)
        else "method not found among public/protected methods",
    )
    return target, structure
