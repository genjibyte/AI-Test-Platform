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
    if provider == "openai":
        from app.llm.openai_client import OpenAIClient

        return OpenAIClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    raise NotImplementedError(
        f"real LLM provider '{provider}' is not wired yet; use 'fake' or 'openai'"
    )
