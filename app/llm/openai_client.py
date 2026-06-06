"""OpenAI chat client (P2-T03 real provider).

Implements the same ``LLMClient`` interface as the fake client, so nothing else
in the codebase changes. The API key is read from settings (env
``TESTAGENT_LLM_API_KEY``) — never hardcoded, never logged. Forces JSON output
via ``response_format={"type": "json_object"}`` and temperature 0 for stability.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.llm.client import LLMClient, LLMRequestError, LLMResponse

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"

_SYSTEM = (
    "You are a senior Java test engineer. "
    "Respond with a single JSON object only, no prose, no markdown fences."
)


class OpenAIClient(LLMClient):
    def __init__(
        self,
        api_key: Optional[str],
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        if not api_key:
            raise ValueError("missing OpenAI API key (set TESTAGENT_LLM_API_KEY)")
        self._api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str) -> LLMResponse:
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise LLMRequestError(f"OpenAI-compatible API request failed: {exc}") from exc
        if resp.status_code >= 400:
            try:
                err = resp.json().get("error", {})
                msg = err.get("message", resp.text)
                code = err.get("code") or err.get("type")
            except Exception:  # noqa: BLE001
                msg, code = resp.text, None
            raise LLMRequestError(
                f"OpenAI API {resp.status_code} ({code}): {msg}"
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(
            text=content, provider="openai", model=data.get("model", self.model)
        )
