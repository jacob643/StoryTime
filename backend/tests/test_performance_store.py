import json
from pathlib import Path

from backend.game_logic import Split
from backend.performance_store import (
    PERFORMANCE_PATH,
    load_performance,
    reset_performance,
    save_performance,
)


class TestLoadEmpty:
    def test_no_file_returns_empty(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        assert load_performance() == []

    def test_corrupt_file_returns_empty(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        p.write_text("not json", encoding="utf-8")
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        assert load_performance() == []

    def test_non_list_returns_empty(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        assert load_performance() == []


class TestSaveAndLoad:
    def test_save_then_load(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        splits = [Split(300.0, 50), Split(320.0, 50)]
        save_performance(splits)
        assert p.exists()
        loaded = load_performance()
        assert len(loaded) == 2
        assert loaded[0].speed_cpm == 300.0
        assert loaded[0].char_count == 50
        assert loaded[1].speed_cpm == 320.0
        assert loaded[1].char_count == 50

    def test_roundtrip_preserves_order(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        splits = [Split(100.0, 30), Split(200.0, 40), Split(300.0, 50)]
        save_performance(splits)
        loaded = load_performance()
        assert [s.speed_cpm for s in loaded] == [100.0, 200.0, 300.0]

    def test_save_empty_list(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        save_performance([])
        assert p.exists()
        assert json.loads(p.read_text(encoding="utf-8")) == []


class TestReset:
    def test_reset_removes_file(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        save_performance([Split(300.0, 50)])
        assert p.exists()
        reset_performance()
        assert not p.exists()

    def test_reset_no_file_no_error(self, monkeypatch, tmp_path):
        p = tmp_path / "performance.json"
        monkeypatch.setattr("backend.performance_store.PERFORMANCE_PATH", p)
        assert not p.exists()
        reset_performance()  # should not raise
