"""Offline generation dry-run (P2-T03).

Runs the full contract loop: context -> prompt -> LLM client -> parse -> assemble.
Uses the FAKE client by default. This DOES NOT write files or execute anything —
it only proves the prompt/context/output-schema contracts are stable end to end.
File writing (P2-T06) and execution (P2-T07) are separate later tasks.
"""
from __future__ import annotations

from typing import Optional

from app.generate.prompt_builder import build_prompt
from app.llm.client import LLMClient, get_client
from app.llm.schema import TestGenerationResult, assemble_result, parse_payload
from app.models.context_snapshot import ContextSnapshot


def dry_generate(
    context: ContextSnapshot, client: Optional[LLMClient] = None
) -> TestGenerationResult:
    client = client or get_client()
    prompt = build_prompt(context)
    response = client.generate(prompt)
    payload = parse_payload(response.text)
    return assemble_result(context, payload, model=response.model)
