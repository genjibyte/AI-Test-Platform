"""Context Snapshot + target models (P2-T01).

The snapshot is the *bounded* context handed to a future generator. It contains
only what docs/07 §P4 allows, in priority order. NO whole-repo dumps.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.java_source import JavaClassStructure, JavaConstructor, JavaField


class Target(BaseModel):
    target_class: str                       # fully-qualified class name
    target_method: Optional[str] = None     # method name (optional)
    file_path: Optional[str] = None         # relative path if resolved
    exists: bool = False
    method_exists: Optional[bool] = None
    reason: Optional[str] = None


class DependencySummary(BaseModel):
    group_id: str
    artifact_id: str
    version: Optional[str] = None
    scope: Optional[str] = None


class BuildConstraints(BaseModel):
    java_source: Optional[str] = None
    java_target: Optional[str] = None
    java_release: Optional[str] = None


class NeighborTestSummary(BaseModel):
    found: bool = False
    file_path: Optional[str] = None
    class_name: Optional[str] = None
    test_methods: List[str] = Field(default_factory=list)
    source_excerpt: Optional[str] = None  # bounded snippet for style/mock imitation (v2)


class ContextSnapshot(BaseModel):
    target_class: str
    target_method: Optional[str] = None

    # P4 priority-ordered bounded context
    target_method_source: Optional[str] = None      # 1. target method source
    class_structure: JavaClassStructure             # 2. target class structure
    imports: List[str] = Field(default_factory=list)               # 3. imports
    constructors: List[JavaConstructor] = Field(default_factory=list)  # 4. ctors
    fields: List[JavaField] = Field(default_factory=list)             # 5. fields
    neighbor_test: NeighborTestSummary = Field(default_factory=NeighborTestSummary)  # 6.
    maven_dependencies: List[DependencySummary] = Field(default_factory=list)        # 7.
    build_constraints: BuildConstraints = Field(default_factory=BuildConstraints)    # 8.
