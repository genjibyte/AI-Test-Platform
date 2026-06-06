"""Stable LLM I/O contract (P2-T03).

Two layers, kept deliberately separate:

- ``LLMTestPayload``  — the EXACT JSON the model must return. The model only
  controls creative fields (imports, test source, scenarios, mocks, notes).
- ``TestGenerationResult`` — the full result the platform assembles, where the
  target identity / file naming / ``trusted`` flag are filled DETERMINISTICALLY
  by us (the model cannot corrupt them). ``trusted`` is always False (docs/07 P2).

This separation makes the contract robust: malformed or adversarial model output
can never change which class/method/file we are talking about.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

from app.models.context_snapshot import ContextSnapshot


class LLMOutputError(Exception):
    """Raised when model output cannot be parsed/validated against the contract."""


class LLMTestPayload(BaseModel):
    """The model-controlled JSON contract. No extra keys are required.

    Prompt/Context v2 adds OPTIONAL grounding metadata (default-empty, so v1
    payloads and the offline fake still validate). These make the model declare
    what it grounded on and what it deliberately skipped — a cheap self-check
    that reduces API/oracle hallucination, and a signal the human reviewer sees.
    """

    model_config = {"extra": "ignore"}

    imports: List[str] = Field(default_factory=list)
    test_source: str
    scenarios: List[str] = Field(default_factory=list)
    mocks: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    # v2 grounding metadata (optional)
    used_apis: List[str] = Field(default_factory=list)            # APIs used, must be in context
    behavior_sources: List[str] = Field(default_factory=list)     # evidence backing each oracle
    omitted_uncertain_cases: List[str] = Field(default_factory=list)  # cases skipped, not guessed
    dependency_assumptions: List[str] = Field(default_factory=list)   # assumed JUnit/Mockito facts
    risk_flags: List[str] = Field(default_factory=list)           # self-declared risky choices


class TestGenerationResult(BaseModel):
    """Full, platform-assembled generation result."""

    __test__ = False  # not a pytest test class despite the 'Test' prefix

    target_class: str
    target_method: Optional[str] = None
    package: Optional[str] = None
    test_class_name: str
    file_name: str
    imports: List[str] = Field(default_factory=list)
    test_source: str
    scenarios: List[str] = Field(default_factory=list)
    mocks: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    model: Optional[str] = None
    trusted: bool = False  # generated tests are NEVER trusted (docs/07 P2)

    # v2 grounding metadata (carried from the payload; optional)
    used_apis: List[str] = Field(default_factory=list)
    behavior_sources: List[str] = Field(default_factory=list)
    omitted_uncertain_cases: List[str] = Field(default_factory=list)
    dependency_assumptions: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)


def _extract_json(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start: end + 1]
    return text


def parse_payload(text: str) -> LLMTestPayload:
    """Extract + validate the model JSON. Explicit failure on bad output."""
    raw = _extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMOutputError(f"model output is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMOutputError("model output JSON is not an object")
    try:
        return LLMTestPayload(**data)
    except ValidationError as exc:
        raise LLMOutputError(f"model output failed schema validation: {exc}") from exc


def assemble_result(
    context: ContextSnapshot, payload: LLMTestPayload, model: Optional[str] = None
) -> TestGenerationResult:
    """Merge deterministic identity (from context) with model-controlled fields."""
    simple = context.target_class.rsplit(".", 1)[-1]
    test_class_name = f"{simple}AiGeneratedTest"
    return TestGenerationResult(
        target_class=context.target_class,
        target_method=context.target_method,
        package=context.class_structure.package,
        test_class_name=test_class_name,
        file_name=f"{test_class_name}.java",
        imports=payload.imports,
        test_source=payload.test_source,
        scenarios=payload.scenarios,
        mocks=payload.mocks,
        notes=payload.notes,
        model=model,
        trusted=False,
        used_apis=payload.used_apis,
        behavior_sources=payload.behavior_sources,
        omitted_uncertain_cases=payload.omitted_uncertain_cases,
        dependency_assumptions=payload.dependency_assumptions,
        risk_flags=payload.risk_flags,
    )
