from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


def test_list_models_returns_providers(client):
    mock_providers = [
        {"provider": "ollama", "available": True, "models": ["llama3.2:3b"]},
        {"provider": "custom", "available": True, "models": ["gpt-4"]},
    ]
    with patch(
        "backend.providers.registry.registry.discover",
        new_callable=AsyncMock,
        return_value=mock_providers,
    ):
        r = client.get("/api/models")
    assert r.status_code == 200
    data = r.json()
    assert len(data["providers"]) == 2
    assert data["providers"][0]["provider"] == "ollama"
    assert data["providers"][1]["models"] == ["gpt-4"]


def test_list_models_returns_empty_when_no_providers(client):
    with patch(
        "backend.providers.registry.registry.discover",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r = client.get("/api/models")
    assert r.status_code == 200
    assert r.json()["providers"] == []
