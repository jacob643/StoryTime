from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.session import session_store


@pytest.fixture(autouse=True)
def enable_dev_mode():
    saved = settings.dev_mode
    settings.dev_mode = True
    yield
    settings.dev_mode = saved


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    from backend.settings_manager import GameSettings, load_settings as real_load
    monkeypatch.setattr("backend.settings_manager.load_settings", lambda: GameSettings())
    import backend.settings_manager
    backend.settings_manager._game_settings = None
    app.dependency_overrides.clear()
    session_store._sessions.clear()
    with TestClient(app) as c:
        yield c


def _mock_ollama_response(status_code: int, json_data: dict | None = None):
    resp = httpx.Response(status_code, request=httpx.Request("POST", "http://ollama/api/generate"))
    if json_data is not None:
        resp._content = httpx.Response(200, json=json_data).content
        resp.json = lambda: json_data
    return resp


def test_simulate_returns_403_when_dev_mode_off(client):
    settings.dev_mode = False
    response = client.post("/api/simulate", json={"simulated_speed_cpm": 85.0})
    assert response.status_code == 403
    assert response.json()["detail"] == "Dev mode is disabled"


def test_simulate_without_session_uses_fixed_thresholds(client):
    mock_resp = _mock_ollama_response(200, {"response": "Simulated paragraph..."})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        response = client.post("/api/simulate", json={"simulated_speed_cpm": 85.0})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Simulated paragraph..."
    assert data["outcome_tier"] == 3
    assert data["outcome_label"] == "positive"


def test_simulate_with_session_uses_adaptive_scoring(client):
    mock_resp1 = _mock_ollama_response(200, {"response": "First paragraph..."})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp1):
        first = client.post("/api/generate", json={"prompt": "Tell a story"})
    session_id = first.json()["session_id"]

    # Seed rolling window with 5 split speeds
    session = session_store.get(session_id)
    session.rolling_splits = [50.0, 55.0, 60.0, 45.0, 52.0]

    mock_resp2 = _mock_ollama_response(200, {"response": "Simulated outcome..."})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp2):
        response = client.post("/api/simulate", json={
            "session_id": session_id,
            "simulated_speed_cpm": 300.0,
        })

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Simulated outcome..."
    # 300 CPM is way above avg of ~52 CPM + many sigmas → tier 4
    assert data["outcome_tier"] == 4
    assert data["outcome_label"] == "very positive"


def test_simulate_returns_404_for_nonexistent_session(client):
    response = client.post("/api/simulate", json={
        "session_id": "nonexistent",
        "simulated_speed_cpm": 85.0,
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_simulate_appends_to_session_history(client):
    mock_resp1 = _mock_ollama_response(200, {"response": "First paragraph of a story about something interesting and long enough to pass validation."})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp1):
        first = client.post("/api/generate", json={"prompt": "Tell a story"})
    session_id = first.json()["session_id"]

    session_before = session_store.get(session_id)
    hist_len_before = len(session_before.history)

    mock_resp2 = _mock_ollama_response(200, {"response": "Simulated next paragraph that is long enough to be valid."})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp2):
        resp = client.post("/api/simulate", json={
            "session_id": session_id,
            "simulated_speed_cpm": 100.0,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id

    session_after = session_store.get(session_id)
    assert len(session_after.history) == hist_len_before + 1
    record = session_after.history[-1]
    assert record.speed_cpm == 100.0
    assert record.outcome_tier == data["outcome_tier"]


def test_simulate_returns_503_on_llm_error(client):
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("Timed out"),
    ):
        response = client.post("/api/simulate", json={"simulated_speed_cpm": 85.0})

    assert response.status_code == 503
    assert "error" in response.json()["detail"].lower()


def test_simulate_returns_422_without_simulated_speed_cpm(client):
    response = client.post("/api/simulate", json={})
    assert response.status_code == 422
