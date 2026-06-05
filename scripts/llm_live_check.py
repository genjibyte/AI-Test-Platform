"""Live LLM contract stability check (P2-T03).

Builds the bounded Context Snapshot for samples/calc#max, sends the deterministic
prompt to the configured provider N times, and validates every response against
``LLMTestPayload``. Reports how many rounds were schema-valid.

Run (key via env, never committed)::

    set TESTAGENT_LLM_PROVIDER=openai
    set TESTAGENT_LLM_MODEL=gpt-4o-mini
    set TESTAGENT_LLM_API_KEY=sk-...
    python -m scripts.llm_live_check 3
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.context.context_collector import build_snapshot
from app.generate.prompt_builder import build_prompt
from app.llm.client import LLMRequestError, get_client
from app.llm.schema import LLMOutputError, parse_payload

REPO = Path(__file__).resolve().parents[1] / "samples" / "calc"


def main(rounds: int = 3) -> int:
    context = build_snapshot(REPO, "com.example.Calc", "max")
    prompt = build_prompt(context)
    client = get_client()

    ok = 0
    last_model = None
    for i in range(1, rounds + 1):
        try:
            resp = client.generate(prompt)
        except LLMRequestError as exc:
            print(f"[round {i}] REQUEST FAIL: {exc}")
            continue
        last_model = resp.model
        try:
            payload = parse_payload(resp.text)
        except LLMOutputError as exc:
            print(f"[round {i}] SCHEMA FAIL: {exc}")
            print(f"           raw[:300]={resp.text[:300]!r}")
            continue
        ok += 1
        has_assert = "assert" in payload.test_source.lower()
        print(
            f"[round {i}] OK  imports={len(payload.imports)} "
            f"scenarios={len(payload.scenarios)} mocks={len(payload.mocks)} "
            f"test_source_len={len(payload.test_source)} has_assertion={has_assert}"
        )

    print(f"\nstability: {ok}/{rounds} schema-valid  (provider model={last_model})")
    return 0 if ok == rounds else 1


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    raise SystemExit(main(n))
