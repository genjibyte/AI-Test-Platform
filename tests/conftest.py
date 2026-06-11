"""Global test-safety guards (foundation hardening, P1-T2).

Two layers stop the unit suite from ever contacting a real LLM/API, even if a local
``.env`` sets a real ``TESTAGENT_LLM_PROVIDER``:

1. ``pytest_configure`` forces ``TESTAGENT_LLM_PROVIDER=fake`` (an ``os.environ``
   override, which takes precedence over the ``.env`` file in pydantic-settings), so
   any ``get_settings()`` / ``get_client()`` with no explicit provider resolves to the
   offline ``FakeLLMClient``.
2. an autouse fixture blocks the OpenAI/DeepSeek HTTP call at the ``httpx`` boundary,
   so even an explicitly-constructed real client cannot reach the network.

Both layers are bypassed only when ``TESTAGENT_E2E=1`` (the explicit opt-in the e2e
suite already uses). This file never reads or prints ``.env`` contents — it only sets
an env override. Per-test monkeypatching in individual tests still runs after these
guards and therefore still wins (e.g. ``test_openai_generate_wraps_httpx_errors``
re-patches ``httpx.post`` to assert error wrapping).
"""
import os

import pytest

_E2E_OPT_IN = os.environ.get("TESTAGENT_E2E") == "1"


def pytest_configure(config):  # noqa: ARG001 - pytest hook signature
    """Hard default: offline fake provider for the whole unit suite."""
    if _E2E_OPT_IN:
        return
    os.environ["TESTAGENT_LLM_PROVIDER"] = "fake"
    # Drop any cached Settings so the override is picked up on next read.
    try:
        from app.config import get_settings

        get_settings.cache_clear()
    except Exception:  # noqa: BLE001 - safety net must never break collection
        pass


@pytest.fixture(autouse=True)
def _block_real_llm_network(monkeypatch):
    """Belt-and-suspenders: block the real provider's HTTP call so no test can reach
    the network. Tests that mock ``httpx`` themselves override this (their monkeypatch
    runs after fixture setup). Opt out of both guards with ``TESTAGENT_E2E=1``."""
    if _E2E_OPT_IN:
        return

    def _blocked(*_args, **_kwargs):
        raise RuntimeError(
            "real LLM HTTP call blocked during tests (set TESTAGENT_E2E=1 to opt in)"
        )

    try:
        import app.llm.openai_client  # noqa: F401 - ensure the module exists

        monkeypatch.setattr(
            "app.llm.openai_client.httpx.post", _blocked, raising=False
        )
    except Exception:  # noqa: BLE001 - if the module/dep is absent, nothing to block
        pass
