from pathlib import Path

import pytest

from backend.game_logic import Split
from backend.session import GameSession, ParagraphRecord, SessionStore


@pytest.fixture(autouse=True)
def no_persisted_performance(monkeypatch):
    monkeypatch.setattr("backend.session.load_performance", lambda: [])


class TestCreateSession:
    def test_create_session(self):
        store = SessionStore()
        session = store.create(initial_prompt="test prompt")
        assert session.id is not None
        assert session.initial_prompt == "test prompt"
        assert session.history == []
        assert session.current_outcome_tier == 0
        assert len(session.rolling_window) == 0
        assert session.initial_avg_cpm == 300.0
        assert session.scoring_params is not None

    def test_create_seeds_from_performance(self, monkeypatch):
        monkeypatch.setattr("backend.session.load_performance", lambda: [
            Split(250.0, 50),
            Split(350.0, 50),
            Split(300.0, 50),
        ])
        store = SessionStore()
        session = store.create()
        assert len(session.rolling_window) == 3
        assert session.rolling_window.total_chars == 150

    def test_create_with_empty_performance(self, monkeypatch):
        monkeypatch.setattr("backend.session.load_performance", lambda: [])
        store = SessionStore()
        session = store.create()
        assert len(session.rolling_window) == 0

    def test_create_session_default_initial_prompt(self):
        store = SessionStore()
        session = store.create()
        assert session.initial_prompt == ""

    def test_create_session_custom_avg(self):
        store = SessionStore()
        session = store.create(initial_prompt="test", initial_avg_cpm=400.0)
        assert session.initial_avg_cpm == 400.0


class TestGetSession:
    def test_get_existing_session(self):
        store = SessionStore()
        created = store.create()
        retrieved = store.get(created.id)
        assert retrieved is created

    def test_get_nonexistent_session(self):
        store = SessionStore()
        assert store.get("nonexistent-id") is None


class TestAppendParagraph:
    def test_append_paragraph(self):
        store = SessionStore()
        session = store.create()

        record = store.append_paragraph(
            session_id=session.id,
            text="test paragraph",
            speed_cpm=300.0,
            time_taken_ms=5000,
            accuracy=0.95,
            outcome_tier=2,
        )

        assert record is not None
        assert record.text == "test paragraph"
        assert record.speed_cpm == 300.0
        assert record.time_taken_ms == 5000
        assert record.accuracy == 0.95
        assert record.outcome_tier == 2
        assert record.splits == []
        assert len(session.history) == 1
        assert len(session.rolling_window) == 0

    def test_append_paragraph_with_splits(self):
        store = SessionStore()
        session = store.create()
        splits = [Split(300.0, 50), Split(320.0, 50)]

        record = store.append_paragraph(
            session_id=session.id,
            text="test",
            speed_cpm=310.0,
            time_taken_ms=4000,
            accuracy=1.0,
            outcome_tier=3,
            splits=splits,
        )

        assert record.splits == splits
        assert list(session.rolling_window.splits) == splits

    def test_splits_extend_rolling_window(self):
        store = SessionStore()
        session = store.create()

        store.append_paragraph(session.id, "p1", 300, 1000, 1.0, 2, splits=[Split(100, 50), Split(200, 50), Split(300, 50)])
        store.append_paragraph(session.id, "p2", 310, 1000, 1.0, 3, splits=[Split(400, 50), Split(500, 50), Split(600, 50)])

        speeds = [s.speed_cpm for s in session.rolling_window.splits]
        assert speeds == [100, 200, 300, 400, 500, 600]

    def test_rolling_window_max_2500_chars(self):
        store = SessionStore()
        session = store.create()

        for i in range(17):
            store.append_paragraph(session.id, f"p{i}", 300, 1000, 1.0, 2, splits=[Split(float(i), 50)] * 3)

        assert session.rolling_window.total_chars <= 2500
        # 17 paragraphs × 3 splits × 50 chars = 2550 total → 1 split (50 chars) should be evicted
        assert 2450 <= session.rolling_window.total_chars <= 2500

    def test_append_paragraph_multiple(self):
        store = SessionStore()
        session = store.create()

        r1 = store.append_paragraph(session.id, "first", 100.0, 2000, 0.9, 0)
        r2 = store.append_paragraph(session.id, "second", 400.0, 3000, 0.95, 3)

        assert r1 is not None
        assert r2 is not None
        assert len(session.history) == 2
        assert session.history[0] is r1
        assert session.history[1] is r2

    def test_append_paragraph_nonexistent_session(self):
        store = SessionStore()
        record = store.append_paragraph(
            session_id="bad-id",
            text="test",
            speed_cpm=100.0,
            time_taken_ms=1000,
            accuracy=1.0,
            outcome_tier=0,
        )
        assert record is None

    def test_sessions_are_independent(self):
        store = SessionStore()
        s1 = store.create("prompt 1")
        s2 = store.create("prompt 2")

        store.append_paragraph(s1.id, "s1 paragraph", 200.0, 4000, 0.9, 1)

        assert len(s1.history) == 1
        assert len(s2.history) == 0

    def test_paragraph_record_immutable_fields(self):
        r = ParagraphRecord(text="hello", speed_cpm=150.0, time_taken_ms=3000, accuracy=0.88, outcome_tier=1)
        assert r.text == "hello"
        assert r.speed_cpm == 150.0
        assert r.time_taken_ms == 3000
        assert r.accuracy == 0.88
        assert r.outcome_tier == 1

    def test_append_paragraph_does_not_touch_disk(self, monkeypatch, tmp_path):
        """Story files are written by the route layer, not by the session store."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        store = SessionStore()
        session = store.create(initial_prompt="test story")

        store.append_paragraph(
            session_id=session.id,
            text="Once upon a time.",
            speed_cpm=250.0,
            time_taken_ms=5000,
            accuracy=0.95,
            outcome_tier=2,
            splits=[Split(200.0, 50), Split(300.0, 50)],
        )

        assert not (tmp_path / "writtenStories").exists()
        assert len(session.history) == 1


class TestResumeStory:
    def test_resume_restores_premise_and_history(self, monkeypatch, tmp_path):
        from datetime import datetime

        from backend import story_file

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr("backend.session.load_performance", lambda: [])
        story_file.clear_cache()

        story = story_file.create_story("a bar of soap", "First paragraph.")
        story_file.complete_current(story, 312.4, 1, completed_at=datetime(2026, 10, 29, 12, 46, 10))
        story_file.append_paragraph(story, "Second paragraph.")
        loaded = story_file.load_story(story.story_id)
        assert loaded is not None

        store = SessionStore()
        session = store.resume(loaded)

        assert session.story_id == story.story_id
        assert session.initial_prompt == "a bar of soap"
        assert len(session.history) == 1
        assert session.history[0].text == "First paragraph."
        assert session.history[0].speed_cpm == 312.4
        assert session.history[0].outcome_tier == 1
        assert store.get_live_by_story(story.story_id) is session

    def test_resume_reuses_live_session(self, monkeypatch, tmp_path):
        from backend import story_file

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr("backend.session.load_performance", lambda: [])
        story = story_file.create_story("premise", "First.")
        store = SessionStore()

        first = store.resume(story)
        second = store.resume(story)

        assert first is second
