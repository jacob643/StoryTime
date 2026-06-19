from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


def _mock_ollama_response(status_code: int, json_data: dict | None = None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


async def test_generate_returns_200_and_response(client):
    mock_resp = _mock_ollama_response(200, {"response": "A brave warrior..."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 200
    assert response.json() == {"response": "A brave warrior..."}


async def test_generate_returns_422_without_prompt(client):
    response = client.post("/api/generate", json={})
    assert response.status_code == 422


async def test_health_returns_ollama_available_true(client):
    mock_resp = _mock_ollama_response(200)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ollama_available": True}


async def test_health_returns_ollama_available_false(client):
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.RequestError("Connection refused"),
    ):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ollama_available": False}
