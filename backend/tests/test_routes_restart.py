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


def test_restart_creates_new_session_and_returns_paragraph(client):
    mock_resp = _mock_ollama_response(200, {"response": "A new story begins..."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post("/api/restart", json={"initial_prompt": "Write a tale"})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "A new story begins..."
    assert data["session_id"] is not None
    assert data["outcome_tier"] == 2
    assert data["outcome_label"] == "neutral"


def test_restart_returns_422_without_initial_prompt(client):
    response = client.post("/api/restart", json={})
    assert response.status_code == 422


def test_restart_returns_503_on_llm_timeout(client):
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("Timed out"),
    ):
        response = client.post("/api/restart", json={"initial_prompt": "Write a tale"})

    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"].lower()
