from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.prompt_engine import NEUTRAL_FALLBACK


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
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
    assert "error" in response.json()["detail"].lower()


def test_generate_returns_503_on_llm_connection_error(client):
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 503
    assert "error" in response.json()["detail"].lower()


def test_generate_returns_503_on_ollama_500(client):
    mock_resp = httpx.Response(500, request=httpx.Request("POST", "http://ollama/api/generate"))

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 503
    assert "error" in response.json()["detail"].lower()


def test_generate_returns_422_without_prompt(client):
    response = client.post("/api/generate", json={})
    assert response.status_code == 422


def test_generate_subsequent_call_uses_fixed_fallback(client):
    mock_resp = _mock_ollama_response(200, {"response": "A brave warrior..."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        first = client.post("/api/generate", json={"prompt": "Tell a story"})

    session_id = first.json()["session_id"]

    mock_resp2 = _mock_ollama_response(200, {"response": "The dragon approached..."})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp2):
        second = client.post("/api/generate", json={
            "prompt": "A brave warrior...",
            "session_id": session_id,
            "splits": [{"speed_cpm": 425.0, "char_count": 50}],
        })

    assert second.status_code == 200
    data = second.json()
    assert data["response"] == "The dragon approached..."
    assert data["session_id"] == session_id


def test_generate_subsequent_call_with_splits(client):
    mock_resp = _mock_ollama_response(200, {"response": "First paragraph..."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        first = client.post("/api/generate", json={"prompt": "Tell a story"})

    session_id = first.json()["session_id"]

    mock_resp2 = _mock_ollama_response(200, {"response": "Second paragraph..."})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp2):
        second = client.post("/api/generate", json={
            "prompt": "First paragraph...",
            "session_id": session_id,
            "splits": [
                {"speed_cpm": 280.0, "char_count": 50},
                {"speed_cpm": 290.0, "char_count": 50},
                {"speed_cpm": 310.0, "char_count": 50},
                {"speed_cpm": 320.0, "char_count": 50},
            ],
        })

    assert second.status_code == 200
    data = second.json()
    assert data["response"] == "Second paragraph..."
    assert data["session_id"] == session_id


def test_generate_first_call_fallback_on_empty_response(client):
    mock_resp = _mock_ollama_response(200, {"response": ""})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == NEUTRAL_FALLBACK
    assert data["outcome_tier"] == 2
    assert data["outcome_label"] == "neutral"


def test_generate_first_call_fallback_on_very_short_response(client):
    mock_resp = _mock_ollama_response(200, {"response": "Hi."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post("/api/generate", json={"prompt": "Tell a story"})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == NEUTRAL_FALLBACK


def test_generate_subsequent_call_fallback_to_last_paragraph(client):
    mock_resp = _mock_ollama_response(200, {"response": "A brave warrior entered the cave."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        first = client.post("/api/generate", json={"prompt": "Tell a story"})

    session_id = first.json()["session_id"]
    prev_text = first.json()["response"]

    mock_resp2 = _mock_ollama_response(200, {"response": ""})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp2):
        second = client.post("/api/generate", json={
            "prompt": prev_text,
            "session_id": session_id,
            "splits": [{"speed_cpm": 80.0, "char_count": 50}],
        })

    assert second.status_code == 200
    data = second.json()
    assert data["response"] == prev_text
    assert data["session_id"] == session_id


def test_generate_subsequent_call_unknown_session_returns_404(client):
    response = client.post("/api/generate", json={
        "prompt": "some text",
        "session_id": "nonexistent",
        "splits": [{"speed_cpm": 50.0, "char_count": 50}],
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_health_first_visit(client, monkeypatch, tmp_path):
    """No config file exists → first_visit: true."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_resp = _mock_ollama_response(200)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["first_visit"] is True


def test_health_returning_visitor(client, monkeypatch, tmp_path):
    """Config file exists → first_visit: false."""
    config_dir = tmp_path / ".storytime"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.json"
    config_file.write_text("{}")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    mock_resp = _mock_ollama_response(200)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["first_visit"] is False


def test_health_ollama_running(client):
    mock_resp = _mock_ollama_response(200)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["ollama_running"] is True


def test_health_ollama_down(client):
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.RequestError("Connection refused"),
    ):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["ollama_running"] is False
