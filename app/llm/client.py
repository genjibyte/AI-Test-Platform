"""LLM client interface + factory (P2-T03).

All callers depend on ``LLMClient`` only. ``get_client`` returns the offline
``FakeLLMClient`` by default; real providers are intentionally NOT wired yet and
raise ``NotImplementedError`` so no real model can be contacted by accident.
"""
from __future__ import annotations

import abc
from typing import Optional

from pydantic import BaseModel

from app.config import Settings, get_settings


class LLMRequestError(Exception):
    """Raised when a provider request fails (auth, quota, network, etc.)."""


class LLMResponse(BaseModel):
    text: str
    provider: str
    model: Optional[str] = None


class LLMClient(abc.ABC):
    """Minimal text-in / text-out contract. The only model touch-point."""

    @abc.abstractmethod
    def generate(self, prompt: str) -> LLMResponse:  # pragma: no cover - interface
        ...


def get_client(settings: Optional[Settings] = None) -> LLMClient:
    settings = settings or get_settings()
    provider = (settings.llm_provider or "fake").lower()
    if provider == "fake":
        from app.llm.fake_client import FakeLLMClient

        return FakeLLMClient(model=settings.llm_model or "fake-1")
    if provider in ("openai", "deepseek"):
        from app.llm.openai_client import OpenAIClient

        # DeepSeek is OpenAI-compatible: same chat/completions shape, different
        # default base URL + model.
        if provider == "deepseek":
            base_url = settings.llm_base_url or "https://api.deepseek.com"
            model = settings.llm_model or "deepseek-chat"
        else:
            base_url = settings.llm_base_url
            model = settings.llm_model
        return OpenAIClient(
            api_key=settings.llm_api_key,
            model=model,
            base_url=base_url,
            timeout=settings.llm_timeout_seconds,
        )
    raise NotImplementedError(
        f"real LLM provider '{provider}' is not wired yet; use 'fake', 'openai', or 'deepseek'"
    )
