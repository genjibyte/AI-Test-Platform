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
    raise NotImplementedError(
        f"real LLM provider '{provider}' is not wired yet; keep "
        "TESTAGENT_LLM_PROVIDER=fake until prompt/context/output contracts are confirmed"
    )
