from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


def test_list_models_returns_models(client):
    mock_models = ["llama3.2:3b", "mistral:7b"]
    with patch(
        "backend.routes.models.provider.list_models",
        new_callable=AsyncMock,
        return_value=mock_models,
    ):
        r = client.get("/api/models")
    assert r.status_code == 200
    data = r.json()
    assert data["models"] == mock_models
    assert data["provider"] == "ollama"


def test_list_models_returns_empty_when_no_models(client):
    with patch(
        "backend.routes.models.provider.list_models",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r = client.get("/api/models")
    assert r.status_code == 200
    assert r.json()["models"] == []
