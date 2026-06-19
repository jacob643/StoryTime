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


def test_generate_first_call_creates_session_and_returns_paragraph(client):
    mock_resp = _mock_ollama_response(200, {"response": "A brave warrior..."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "A brave warrior..."
    assert data["session_id"] is not None
    assert data["outcome_tier"] == 2
    assert data["outcome_label"] == "neutral"


def test_generate_returns_503_on_llm_timeout(client):
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("Timed out"),
    ):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"].lower()


def test_generate_returns_503_on_llm_connection_error(client):
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"].lower()


def test_generate_returns_422_without_prompt(client):
    response = client.post("/api/generate", json={})
    assert response.status_code == 422


def test_generate_subsequent_call_appends_and_returns_next_paragraph(client):
    mock_resp = _mock_ollama_response(200, {"response": "A brave warrior..."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        first = client.post("/api/generate", json={"prompt": "Tell a story"})

    session_id = first.json()["session_id"]

    mock_resp2 = _mock_ollama_response(200, {"response": "The dragon approached..."})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp2):
        second = client.post("/api/generate", json={
            "prompt": "A brave warrior...",
            "session_id": session_id,
            "speed_cpm": 80.0,
        })

    assert second.status_code == 200
    data = second.json()
    assert data["response"] == "The dragon approached..."
    assert data["session_id"] == session_id
    assert data["outcome_tier"] == 3
    assert data["outcome_label"] == "positive"


def test_generate_subsequent_call_unknown_session_returns_404(client):
    response = client.post("/api/generate", json={
        "prompt": "some text",
        "session_id": "nonexistent",
        "speed_cpm": 50.0,
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_health_returns_ollama_available_true(client):
    mock_resp = _mock_ollama_response(200)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ollama_available": True}


def test_health_returns_ollama_available_false(client):
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.RequestError("Connection refused"),
    ):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ollama_available": False}
