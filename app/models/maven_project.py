"""Maven project detection result (P1-T05)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MavenProject(BaseModel):
    is_maven: bool = False
    pom_path: Optional[str] = None          # relative to repo root
    group_id: Optional[str] = None
    artifact_id: Optional[str] = None
    version: Optional[str] = None
    packaging: Optional[str] = None
    java_version: Optional[str] = None
    multi_module: bool = False
    modules: List[str] = Field(default_factory=list)
    main_src: Optional[str] = None          # relative path if present
    test_src: Optional[str] = None
    reason: Optional[str] = None            # why not maven / notes
