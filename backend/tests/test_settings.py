import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.settings_manager import (
    GameSettings,
    load_settings,
    save_settings,
    get_settings,
    update_settings,
)


@pytest.fixture(autouse=True)
def clear_cache():
    import backend.settings_manager as sm
    sm._game_settings = None


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


def _patch_path(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "backend.settings_manager._settings_path",
        lambda: tmp_path / ".storytime" / "config.json",
    )


# --- unit tests ---

def test_game_settings_defaults():
    gs = GameSettings()
    assert gs.scoring_mode == "split"
    assert gs.min_stddev_cpm == 10.0
    assert gs.tier_0_max_sigma == -1.5
    assert gs.tier_1_max_sigma == -0.5
    assert gs.tier_2_max_sigma == 0.5
    assert gs.tier_3_max_sigma == 1.5
    assert gs.paragraph_word_count == 40
    assert gs.target_split_size == 50
    assert gs.min_split_size == 30
    assert len(gs.outcome_directions) == 5
    assert gs.provider == "ollama"
    assert gs.custom_endpoint == ""
    assert gs.custom_api_key == ""
    assert gs.custom_model == ""
    assert gs.ollama_model == "llama3.2:latest"
    assert gs.ignore_case is False


def test_default_fixed_thresholds_values():
    gs = GameSettings()
    assert gs.fixed_thresholds == [300, 350, 400, 450]


def test_save_and_load_roundtrip(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    gs = GameSettings(scoring_mode="fixed", ollama_model="qwen3:latest")
    save_settings(gs)
    import backend.settings_manager as sm
    assert sm._settings_path().exists()
    loaded = load_settings()
    assert loaded.scoring_mode == "fixed"
    assert loaded.ollama_model == "qwen3:latest"


def test_load_returns_defaults_when_no_file(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    gs = load_settings()
    assert gs.scoring_mode == "split"


def test_load_returns_defaults_on_corrupt_file(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    import backend.settings_manager as sm
    sm._settings_path().parent.mkdir(parents=True, exist_ok=True)
    sm._settings_path().write_text("not json", encoding="utf-8")
    gs = load_settings()
    assert gs.scoring_mode == "split"


def test_get_settings_caches(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    gs1 = get_settings()
    gs2 = get_settings()
    assert gs1 is gs2


def test_update_settings_persists(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    updated = update_settings(scoring_mode="fixed")
    assert updated.scoring_mode == "fixed"

    loaded = load_settings()
    assert loaded.scoring_mode == "fixed"


def test_update_settings_ignores_none(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    updated = update_settings(scoring_mode="fixed", tier_0_max_sigma=None)
    assert updated.scoring_mode == "fixed"
    assert updated.tier_0_max_sigma == -1.5  # unchanged from default


def test_update_settings_partial(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    gs = get_settings()
    assert gs.scoring_mode == "split"

    update_settings(scoring_mode="fixed")
    assert get_settings().scoring_mode == "fixed"
    # other fields untouched
    assert get_settings().paragraph_word_count == 40


def test_outcome_directions_roundtrip(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    custom = {
        0: ["custom bad"],
        1: ["custom worse"],
        2: ["custom neutral"],
        3: ["custom good"],
        4: ["custom great"],
    }
    update_settings(outcome_directions=custom)
    loaded = load_settings()
    assert loaded.outcome_directions[2] == ["custom neutral"]
    assert loaded.outcome_directions[0] == ["custom bad"]


def test_outcome_directions_migrates_old_string_format(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    import json
    path = tmp_path / ".storytime" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "outcome_directions": {"0": "old bad", "1": "old worse", "2": "old ok", "3": "old good", "4": "old great"},
    }), encoding="utf-8")
    loaded = load_settings()
    assert loaded.outcome_directions[2] == ["old ok"]
    assert loaded.outcome_directions[0] == ["old bad"]


# --- API tests ---

def test_get_settings_returns_defaults(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["scoring_mode"] == "split"
    assert len(data["outcome_directions"]) == 5
    assert all(isinstance(v, list) for v in data["outcome_directions"].values())
    assert len(data["fixed_thresholds"]) == 4


def test_post_settings_updates_and_returns(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={
        "scoring_mode": "fixed",
        "outcome_directions": {"0": ["bad"], "1": ["worse"], "2": ["ok"], "3": ["good"], "4": ["great"]},
        "fixed_thresholds": [20, 40, 60, 80],
        "target_split_size": 40,
        "min_split_size": 20,
        "min_stddev_cpm": 5.0,
        "tier_0_max_sigma": -2.0,
        "tier_1_max_sigma": -1.0,
        "tier_2_max_sigma": 1.0,
        "tier_3_max_sigma": 2.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["scoring_mode"] == "fixed"
    assert data["outcome_directions"]["2"] == ["ok"]
    assert data["outcome_directions"]["0"] == ["bad"]
    assert data["fixed_thresholds"][0] == 20
    assert data["target_split_size"] == 40


def test_post_partial_update(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={"scoring_mode": "fixed"})
    assert r.status_code == 200
    data = r.json()
    assert data["scoring_mode"] == "fixed"


def test_get_after_post_reflects_changes(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    client.post("/api/settings", json={"scoring_mode": "fixed"})
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["scoring_mode"] == "fixed"


def test_post_settings_provider_fields(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={
        "provider": "custom",
        "custom_endpoint": "https://api.openai.com/v1",
        "custom_api_key": "sk-xxx",
        "custom_model": "gpt-4o",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "custom"
    assert data["custom_endpoint"] == "https://api.openai.com/v1"
    assert data["custom_api_key"] == "sk-xxx"
    assert data["custom_model"] == "gpt-4o"
    assert data["ollama_model"] == "llama3.2:latest"


def test_post_settings_ollama_model(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={"ollama_model": "qwen3:latest"})
    assert r.status_code == 200
    data = r.json()
    assert data["ollama_model"] == "qwen3:latest"


def test_get_settings_includes_provider_defaults(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "ollama"
    assert data["custom_endpoint"] == ""
    assert data["custom_api_key"] == ""
    assert data["custom_model"] == ""
    assert data["ollama_model"] == "llama3.2:latest"
    assert data["ignore_case"] is False


def test_post_settings_ignore_case(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={"ignore_case": True})
    assert r.status_code == 200
    data = r.json()
    assert data["ignore_case"] is True
