from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from starlette.testclient import TestClient

from backend import story_file
from backend.main import app
from backend.session import session_store


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    monkeypatch.setattr(
        "backend.performance_store.PERFORMANCE_PATH",
        tmp_path / "performance.json",
    )
    monkeypatch.setattr("backend.session.load_performance", lambda: [])
    monkeypatch.setattr("backend.routes.stories.load_performance", lambda: [])
    import backend.settings_manager as sm
    monkeypatch.setattr(sm, "_game_settings", sm.GameSettings())
    session_store._sessions.clear()
    session_store._live_by_story.clear()
    story_file.clear_cache()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


def _mock_ollama_response(status_code: int = 200, json_data: dict | None = None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


def _make_story(premise="a bar of soap", completed=0, current="Second paragraph."):
    story = story_file.create_story(premise, "First paragraph.")
    if completed == 0:
        if current is None:
            story_file.complete_current(
                story, 300.0, 2, completed_at=datetime(2026, 10, 29, 12, 0, 0)
            )
        return story

    story_file.complete_current(
        story, 300.0, 2, completed_at=datetime(2026, 10, 29, 12, 0, 0)
    )
    for index in range(completed - 1):
        story_file.append_paragraph(story, f"Paragraph {index + 2}.")
        story_file.complete_current(
            story, 300.0, 2, completed_at=datetime(2026, 10, 29, 12, 0, 0)
        )
    if current is not None:
        story_file.append_paragraph(story, current)
    return story


class TestListStories:
    def test_lists_valid_stories_newest_first(self, client):
        _make_story("first premise")
        _make_story("second premise")

        response = client.get("/api/stories")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert {s["premise"] for s in data["stories"]} == {"first premise", "second premise"}
        assert all(s["has_current"] is True for s in data["stories"])

    def test_skips_invalid_and_old_format_files(self, client):
        directory = Path.cwd() / "writtenStories"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "old_deadbeef.txt").write_text("--- Paragraph 1 ---\nOld text\n", encoding="utf-8")
        (directory / "broken_deadbeef.txt").write_text(
            "Premise: broken\nDate: 2026-10-29 12:00:00\n", encoding="utf-8"
        )
        _make_story("valid premise")

        data = client.get("/api/stories").json()
        assert data["total"] == 1
        assert data["stories"][0]["premise"] == "valid premise"

    def test_filters_and_paginates(self, client):
        for i in range(5):
            _make_story(f"story number {i}")

        data = client.get("/api/stories", params={"q": "number 3"}).json()
        assert data["total"] == 1

        page = client.get("/api/stories", params={"limit": 2, "offset": 1}).json()
        assert page["total"] == 5
        assert len(page["stories"]) == 2

    def test_missing_directory_returns_empty(self, client):
        data = client.get("/api/stories").json()
        assert data == {"stories": [], "total": 0}


class TestStoryDetail:
    def test_detail_returns_paragraphs_and_current(self, client):
        story = _make_story(completed=1, current="Current paragraph.")
        response = client.get(f"/api/stories/{story.story_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["premise"] == "a bar of soap"
        assert len(data["paragraphs"]) == 1
        assert data["paragraphs"][0]["speed_cpm"] == 300.0
        assert data["paragraphs"][0]["outcome_tier"] == 2
        assert data["current"] == "Current paragraph."
        assert len(data["tier_boundaries"]) == 4

    def test_unknown_story_404(self, client):
        assert client.get("/api/stories/does_not_exist").status_code == 404

    def test_invalid_story_id_404(self, client):
        assert client.get("/api/stories/BAD-ID").status_code == 404

    def test_invalid_story_format_422(self, client):
        directory = Path.cwd() / "writtenStories"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "broken_deadbeef.txt").write_text("not a story\n", encoding="utf-8")
        response = client.get("/api/stories/broken_deadbeef")
        assert response.status_code == 422


class TestResume:
    def test_resume_restores_history_and_current(self, client):
        story = _make_story(completed=1, current="Current paragraph.")

        response = client.post(f"/api/stories/{story.story_id}/resume")
        assert response.status_code == 200
        data = response.json()

        assert data["story_id"] == story.story_id
        assert data["premise"] == "a bar of soap"
        assert data["session_id"]
        assert len(data["paragraphs"]) == 1
        assert data["current"] == "Current paragraph."
        assert len(data["tier_boundaries"]) == 4

        session = session_store.get(data["session_id"])
        assert session is not None
        assert session.story_id == story.story_id
        assert len(session.history) == 1

    def test_resume_is_idempotent_for_live_story(self, client):
        story = _make_story(completed=1, current="Current paragraph.")
        first = client.post(f"/api/stories/{story.story_id}/resume").json()
        second = client.post(f"/api/stories/{story.story_id}/resume").json()
        assert first["session_id"] == second["session_id"]

    def test_resume_without_current(self, client):
        story = _make_story(completed=1, current=None)
        data = client.post(f"/api/stories/{story.story_id}/resume").json()
        assert data["current"] is None
        assert len(data["paragraphs"]) == 1

    def test_resume_unknown_story_404(self, client):
        assert client.post("/api/stories/does_not_exist/resume").status_code == 404


class TestContinue:
    def test_returns_existing_current_without_llm(self, client):
        story = _make_story(completed=1, current="Current paragraph.")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            response = client.post(f"/api/stories/{story.story_id}/continue")

        assert response.status_code == 200
        assert response.json()["response"] == "Current paragraph."
        mock_post.assert_not_called()

    def test_generates_and_appends_when_no_current(self, client):
        story = _make_story(completed=1, current=None)

        mock_resp = _mock_ollama_response(json_data={"response": "A generated continuation."})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            response = client.post(f"/api/stories/{story.story_id}/continue")

        assert response.status_code == 200
        assert response.json()["response"] == "A generated continuation."

        loaded = story_file.load_story(story.story_id)
        assert loaded is not None
        assert loaded.current == "A generated continuation."
        assert len(loaded.paragraphs) == 1

    def test_second_continue_is_idempotent(self, client):
        story = _make_story(completed=1, current=None)

        mock_resp = _mock_ollama_response(json_data={"response": "A generated continuation."})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            first = client.post(f"/api/stories/{story.story_id}/continue")
            second = client.post(f"/api/stories/{story.story_id}/continue")

        assert first.json()["response"] == second.json()["response"]
        assert mock_post.call_count == 1

    def test_continue_llm_error_503(self, client):
        story = _make_story(completed=1, current=None)

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            response = client.post(f"/api/stories/{story.story_id}/continue")

        assert response.status_code == 503

    def test_continue_uses_history_and_last_tier(self, client):
        story = _make_story(completed=1, current=None)

        mock_resp = _mock_ollama_response(json_data={"response": "A generated continuation."})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            client.post(f"/api/stories/{story.story_id}/continue")

        prompt = mock_post.call_args.kwargs["json"]["prompt"]
        assert "a bar of soap" in prompt
        assert "First paragraph." in prompt
        assert "Continue the story" in prompt or "direction" in prompt.lower()


class TestGenerationPersistsStory:
    def test_restart_creates_story_file(self, client):
        mock_resp = _mock_ollama_response(json_data={"response": "Opening paragraph text."})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            response = client.post("/api/restart", json={"initial_prompt": "a bar of soap"})

        data = response.json()
        assert data["story_id"]
        story = story_file.load_story(data["story_id"])
        assert story is not None
        assert story.premise == "a bar of soap"
        assert story.current == "Opening paragraph text."
        assert story.paragraphs == []

    def test_generate_writes_metadata_under_typed_paragraph(self, client):
        first_resp = _mock_ollama_response(json_data={"response": "Opening paragraph text."})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=first_resp):
            restart = client.post("/api/restart", json={"initial_prompt": "a bar of soap"}).json()

        second_resp = _mock_ollama_response(json_data={"response": "Second paragraph text."})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=second_resp):
            response = client.post("/api/generate", json={
                "prompt": "Opening paragraph text.",
                "session_id": restart["session_id"],
                "splits": [{"speed_cpm": 312.4, "char_count": 50}],
            })

        assert response.status_code == 200
        assert response.json()["story_id"] == restart["story_id"]

        story = story_file.load_story(restart["story_id"])
        assert story is not None
        assert len(story.paragraphs) == 1
        assert story.paragraphs[0].text == "Opening paragraph text."
        assert story.paragraphs[0].speed_cpm == 312.4
        assert story.current == "Second paragraph text."

        content = story.path.read_text(encoding="utf-8")
        opening_idx = content.index("Opening paragraph text.")
        date_idx = content.index("Date:")
        speed_idx = content.index("Speed:")
        second_idx = content.index("Second paragraph text.")
        assert opening_idx < date_idx < speed_idx < second_idx
        assert "Splits:" not in content

    def test_generate_llm_failure_leaves_story_unchanged(self, client):
        first_resp = _mock_ollama_response(json_data={"response": "Opening paragraph text."})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=first_resp):
            restart = client.post("/api/restart", json={"initial_prompt": "a bar of soap"}).json()

        before = story_file.story_path(restart["story_id"]).read_text(encoding="utf-8")
        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            response = client.post("/api/generate", json={
                "prompt": "Opening paragraph text.",
                "session_id": restart["session_id"],
                "splits": [{"speed_cpm": 312.4, "char_count": 50}],
            })

        assert response.status_code == 503
        after = story_file.story_path(restart["story_id"]).read_text(encoding="utf-8")
        assert after == before
        assert len(session_store.get(restart["session_id"]).history) == 0


class TestDeleteStory:
    def test_delete_removes_file_and_listing(self, client):
        story = _make_story()
        assert story.path.exists()

        response = client.delete(f"/api/stories/{story.story_id}")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert not story.path.exists()
        assert client.get(f"/api/stories/{story.story_id}").status_code == 404
        assert client.get("/api/stories").json() == {"stories": [], "total": 0}

    def test_delete_unknown_story_404(self, client):
        assert client.delete("/api/stories/does_not_exist").status_code == 404

    def test_delete_invalid_id_404(self, client):
        assert client.delete("/api/stories/BAD-ID").status_code == 404

    def test_delete_leaves_other_stories_alone(self, client):
        first = _make_story("first premise")
        second = _make_story("second premise")

        assert client.delete(f"/api/stories/{first.story_id}").status_code == 200
        assert not first.path.exists()
        assert second.path.exists()
        remaining = client.get("/api/stories").json()
        assert remaining["total"] == 1
        assert remaining["stories"][0]["story_id"] == second.story_id

    def test_delete_detaches_live_session(self, client):
        story = _make_story(completed=1, current="Current paragraph.")
        resumed = client.post(f"/api/stories/{story.story_id}/resume").json()
        session_id = resumed["session_id"]

        assert client.delete(f"/api/stories/{story.story_id}").status_code == 200

        assert session_store.get_live_by_story(story.story_id) is None
        session = session_store.get(session_id)
        assert session is not None
        assert session.story is None
        assert session.story_id is None
