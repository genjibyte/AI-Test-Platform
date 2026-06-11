"""Ledger data model (docs/41 section 3). Source-agnostic judged-test record.

A ``JudgedRecord`` is a flat projection of the judging facts the pipeline already
produces (see ``app/benchmark/models.py:BenchCaseResult``) plus *provenance* (who
authored the test) and a content *fingerprint* (for dedup / replay). It adds no new
judgment.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

# Who authored the candidate test. The platform generator is just one author.
AUTHOR_TYPES = ("human", "platform_generator", "external_agent")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint_source(test_source: Optional[str]) -> Optional[str]:
    """sha256 of the whitespace-normalized test source (``None`` when absent).

    Normalizing whitespace means trivial reformatting does not change identity,
    while any token change does -- so re-submissions of the same candidate dedup."""
    if not test_source or not test_source.strip():
        return None
    norm = re.sub(r"\s+", " ", test_source).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


class Provenance(BaseModel):
    """Who/what produced the candidate test. ``author_type`` is one of AUTHOR_TYPES."""

    author_type: str
    author_id: str                       # "alice" | "deepseek-v3" | "copilot" | ...
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    run_id: Optional[str] = None         # e.g. a benchmark run label


class JudgedRecord(BaseModel):
    """One judged candidate test. Judging facts only; no accept/reject verdict."""

    record_id: str
    created_at: str = Field(default_factory=_now_iso)

    # target
    repo_url: str
    ref: Optional[str] = None            # commit/tag pin if known
    target_class: str
    target_method: Optional[str] = None

    # provenance + identity
    provenance: Provenance
    test_fingerprint: Optional[str] = None
    run_kind: Optional[str] = None       # real|fake|dryrun|smoke (docs/43); headline=real

    # judging facts (projected from BenchCaseResult -- no recomputation)
    gen_outcome: Optional[str] = None
    compiled: Optional[bool] = None
    executed: Optional[bool] = None
    passed: Optional[bool] = None
    failure_type: Optional[str] = None
    coverage_status: Optional[str] = None
    target_improved: Optional[bool] = None
    coverage_dropped: Optional[bool] = None
    quality_gate_status: Optional[str] = None
    quality_blockers: int = 0
    quality_warnings: int = 0
    review_recommendation: Optional[str] = None
    conclusion: Optional[str] = None
