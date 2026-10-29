import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.prompt_engine import (
    DEFAULT_CONTINUATION_PROMPT_TEMPLATE,
    DEFAULT_INITIAL_PROMPT_TEMPLATE,
)
from backend.settings_manager import (
    FETCH_TRIGGER_MAX_PCT,
    FETCH_TRIGGER_MIN_PCT,
    GameSettings,
    clamp_fetch_trigger_pct,
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
    assert gs.initial_prompt_template == DEFAULT_INITIAL_PROMPT_TEMPLATE
    assert gs.continuation_prompt_template == DEFAULT_CONTINUATION_PROMPT_TEMPLATE
    assert gs.target_split_size == 50
    assert len(gs.outcome_directions) == 5
    assert gs.provider == "ollama"
    assert gs.custom_endpoint == ""
    assert gs.custom_api_key == ""
    assert gs.custom_model == ""
    assert gs.ollama_model == "llama3.2:latest"
    assert gs.ignore_case is False
    assert gs.fetch_trigger_pct == 75


def test_clamp_fetch_trigger_pct():
    assert clamp_fetch_trigger_pct(-5) == FETCH_TRIGGER_MIN_PCT
    assert clamp_fetch_trigger_pct(9.9) == FETCH_TRIGGER_MIN_PCT
    assert clamp_fetch_trigger_pct(10) == 10
    assert clamp_fetch_trigger_pct(75) == 75
    assert clamp_fetch_trigger_pct(100) == 100
    assert clamp_fetch_trigger_pct(100.1) == FETCH_TRIGGER_MAX_PCT
    assert clamp_fetch_trigger_pct(250) == FETCH_TRIGGER_MAX_PCT


@pytest.mark.parametrize("stored,expected", [(250, 100), (-5, 10)])
def test_load_clamps_legacy_fetch_trigger(monkeypatch, tmp_path, stored, expected):
    _patch_path(monkeypatch, tmp_path)
    import backend.settings_manager as sm
    sm._settings_path().parent.mkdir(parents=True, exist_ok=True)
    sm._settings_path().write_text(
        json.dumps({"fetch_trigger_pct": stored}), encoding="utf-8"
    )
    assert load_settings().fetch_trigger_pct == expected


def test_update_settings_clamps_fetch_trigger(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    assert update_settings(fetch_trigger_pct=250).fetch_trigger_pct == 100
    assert update_settings(fetch_trigger_pct=0).fetch_trigger_pct == 10


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


def test_prompt_templates_roundtrip(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    update_settings(
        initial_prompt_template="Opening {premise}",
        continuation_prompt_template="Continue {premise} with {direction}",
    )
    loaded = load_settings()
    assert loaded.initial_prompt_template == "Opening {premise}"
    assert loaded.continuation_prompt_template == "Continue {premise} with {direction}"


def test_load_legacy_config_uses_default_prompt_templates(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    import backend.settings_manager as sm
    sm._settings_path().parent.mkdir(parents=True, exist_ok=True)
    sm._settings_path().write_text(
        json.dumps({"scoring_mode": "fixed"}), encoding="utf-8"
    )
    loaded = load_settings()
    assert loaded.initial_prompt_template == DEFAULT_INITIAL_PROMPT_TEMPLATE
    assert loaded.continuation_prompt_template == DEFAULT_CONTINUATION_PROMPT_TEMPLATE


def test_load_blank_prompt_templates_falls_back_to_defaults(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    import backend.settings_manager as sm
    sm._settings_path().parent.mkdir(parents=True, exist_ok=True)
    sm._settings_path().write_text(
        json.dumps({
            "initial_prompt_template": "   ",
            "continuation_prompt_template": "",
        }),
        encoding="utf-8",
    )
    loaded = load_settings()
    assert loaded.initial_prompt_template == DEFAULT_INITIAL_PROMPT_TEMPLATE
    assert loaded.continuation_prompt_template == DEFAULT_CONTINUATION_PROMPT_TEMPLATE


def test_update_blank_prompt_template_stores_default(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    updated = update_settings(initial_prompt_template="   ")
    assert updated.initial_prompt_template == DEFAULT_INITIAL_PROMPT_TEMPLATE


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
    assert data["initial_prompt_template"] == DEFAULT_INITIAL_PROMPT_TEMPLATE
    assert data["continuation_prompt_template"] == DEFAULT_CONTINUATION_PROMPT_TEMPLATE


def test_post_settings_updates_and_returns(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={
        "scoring_mode": "fixed",
        "outcome_directions": {"0": ["bad"], "1": ["worse"], "2": ["ok"], "3": ["good"], "4": ["great"]},
        "fixed_thresholds": [20, 40, 60, 80],
        "target_split_size": 40,
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


def test_post_settings_prompt_templates(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    body = {
        "initial_prompt_template": "Open {premise} {style}",
        "continuation_prompt_template": "Continue {premise} {history} {direction}",
    }
    r = client.post("/api/settings", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["initial_prompt_template"] == body["initial_prompt_template"]
    assert data["continuation_prompt_template"] == body["continuation_prompt_template"]

    r = client.get("/api/settings")
    assert r.json()["initial_prompt_template"] == body["initial_prompt_template"]
    assert r.json()["continuation_prompt_template"] == body["continuation_prompt_template"]


def test_post_blank_prompt_template_returns_default(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={"initial_prompt_template": "   "})
    assert r.status_code == 200
    assert r.json()["initial_prompt_template"] == DEFAULT_INITIAL_PROMPT_TEMPLATE


def test_post_prompt_template_too_long(monkeypatch, tmp_path, client):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={"continuation_prompt_template": "x" * 8001})
    assert r.status_code == 422


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


@pytest.mark.parametrize("value", [9.9, 100.1, -5, 250])
def test_post_settings_rejects_out_of_range_fetch_trigger(monkeypatch, tmp_path, client, value):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={"fetch_trigger_pct": value})
    assert r.status_code == 422
    assert get_settings().fetch_trigger_pct == 75


@pytest.mark.parametrize("value", [10, 100])
def test_post_settings_accepts_fetch_trigger_bounds(monkeypatch, tmp_path, client, value):
    _patch_path(monkeypatch, tmp_path)
    r = client.post("/api/settings", json={"fetch_trigger_pct": value})
    assert r.status_code == 200
    assert r.json()["fetch_trigger_pct"] == value
    assert get_settings().fetch_trigger_pct == value
