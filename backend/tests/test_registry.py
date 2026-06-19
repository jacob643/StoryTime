from unittest.mock import AsyncMock, patch

import pytest

from backend.providers.registry import registry


@pytest.fixture(autouse=True)
def reset_registry():
    registry.refresh()


def _run(coro):
    import asyncio
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def test_registry_default_active_is_ollama():
    assert registry.active.provider_id == "ollama"


def test_registry_default_active_model():
    from backend.config import settings
    assert registry.active_model == settings.default_model


def test_registry_active_switches_to_custom():
    from backend.settings_manager import update_settings
    update_settings(provider="custom", custom_endpoint="https://api.example.com/v1", custom_api_key="sk-test")
    registry.refresh()
    assert registry.active.provider_id == "custom"
    update_settings(provider="ollama", custom_endpoint="", custom_api_key="")
    registry.refresh()


def test_registry_active_model_returns_custom_model():
    from backend.settings_manager import update_settings
    update_settings(provider="custom", custom_endpoint="https://api.example.com/v1", custom_model="gpt-4")
    registry.refresh()
    assert registry.active_model == "gpt-4"
    update_settings(provider="ollama", custom_endpoint="", custom_model="")
    registry.refresh()


def test_registry_falls_back_to_ollama_when_custom_not_configured():
    from backend.settings_manager import update_settings
    update_settings(provider="custom")
    registry.refresh()
    assert registry.active.provider_id == "ollama"
    update_settings(provider="ollama")
    registry.refresh()


def test_registry_discover_includes_ollama():
    with patch.object(registry._ollama, "list_models", new_callable=AsyncMock, return_value=["llama3.2:3b"]):
        result = _run(registry.discover())
    assert any(p["provider"] == "ollama" and p["available"] is True for p in result)


def test_registry_discover_includes_custom_when_configured():
    from backend.settings_manager import update_settings

    update_settings(custom_endpoint="https://api.example.com/v1", custom_api_key="sk-test")
    registry.refresh()

    with patch.object(registry._ollama, "list_models", new_callable=AsyncMock, return_value=[]):
        with patch.object(registry._custom, "list_models", new_callable=AsyncMock, return_value=["gpt-4"]):
            result = _run(registry.discover())
    assert any(p["provider"] == "custom" for p in result)

    update_settings(custom_endpoint="", custom_api_key="")
    registry.refresh()


def test_registry_generate_delegates_to_active():
    from backend.settings_manager import update_settings

    update_settings(provider="custom", custom_endpoint="https://api.example.com/v1", custom_api_key="sk-test")
    registry.refresh()

    with patch.object(registry._custom, "generate", new_callable=AsyncMock, return_value="custom response"):
        result = _run(registry.generate("hello"))
    assert result == "custom response"

    update_settings(provider="ollama", custom_endpoint="", custom_api_key="")
    registry.refresh()


def test_registry_is_available_delegates_to_active():
    with patch.object(registry._ollama, "is_available", new_callable=AsyncMock, return_value=True):
        assert _run(registry.is_available()) is True
