"""Lightweight Java source structure models (P2-T01).

Phase 2 collects *bounded* context. These models hold the structural facts a
later generator needs, extracted by a heuristic parser (no external Java
toolchain). They are descriptive only — no code is generated here.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class JavaParam(BaseModel):
    type: str
    name: str


class JavaField(BaseModel):
    modifiers: List[str] = Field(default_factory=list)
    type: str
    name: str
    raw: str


class JavaConstructor(BaseModel):
    modifiers: List[str] = Field(default_factory=list)
    name: str
    params: List[JavaParam] = Field(default_factory=list)
    signature: str
    source: str


class JavaMethod(BaseModel):
    modifiers: List[str] = Field(default_factory=list)
    return_type: str
    name: str
    params: List[JavaParam] = Field(default_factory=list)
    throws: List[str] = Field(default_factory=list)
    signature: str
    source: str


class JavaClassStructure(BaseModel):
    package: Optional[str] = None
    imports: List[str] = Field(default_factory=list)
    class_name: str
    kind: str = "class"  # class | interface | enum | record
    fields: List[JavaField] = Field(default_factory=list)
    constructors: List[JavaConstructor] = Field(default_factory=list)
    methods: List[JavaMethod] = Field(default_factory=list)  # public/protected only
    nested_classes: List[str] = Field(default_factory=list)  # simple names of nested types
    file_path: Optional[str] = None  # relative to repo root
