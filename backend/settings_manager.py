from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

from backend.game_logic import (
    DEFAULT_MIN_STDDEV_CPM,
    FIXED_THRESHOLDS,
    ScoringParams,
)
from backend.prompt_engine import OUTCOME_DIRECTIONS, _normalize_directions


def _default_fixed_thresholds() -> list[float]:
    return list(FIXED_THRESHOLDS)


def _default_outcome_directions() -> Dict[int, list[str]]:
    return {k: list(v) for k, v in OUTCOME_DIRECTIONS.items()}


@dataclass
class GameSettings:
    scoring_mode: str = "split"
    min_stddev_cpm: float = DEFAULT_MIN_STDDEV_CPM
    tier_0_max_sigma: float = -1.5
    tier_1_max_sigma: float = -0.5
    tier_2_max_sigma: float = 0.5
    tier_3_max_sigma: float = 1.5
    fixed_thresholds: list[float] = field(default_factory=_default_fixed_thresholds)
    paragraph_word_count: int = 40
    target_split_size: int = 50
    min_split_size: int = 30
    outcome_directions: Dict[int, list[str]] = field(default_factory=_default_outcome_directions)
    temperature: float = 2.0
    top_k: int = 40
    top_p: float = 0.9
    provider: str = "ollama"
    custom_endpoint: str = ""
    custom_api_key: str = ""
    custom_model: str = ""
    ollama_model: str = "llama3.2:latest"
    ignore_case: bool = False


def _settings_path() -> Path:
    return Path.home() / ".storytime" / "config.json"


def _coerce_keys(d: dict) -> dict[int, Union[str, list[str]]]:
    return {int(k): v for k, v in d.items()}


def build_scoring_params(gs: GameSettings) -> ScoringParams:
    return ScoringParams(
        mode=gs.scoring_mode,
        min_stddev_cpm=gs.min_stddev_cpm,
        tier_0_max_sigma=gs.tier_0_max_sigma,
        tier_1_max_sigma=gs.tier_1_max_sigma,
        tier_2_max_sigma=gs.tier_2_max_sigma,
        tier_3_max_sigma=gs.tier_3_max_sigma,
        fixed_thresholds=gs.fixed_thresholds,
    )


def _migrate_fixed_thresholds(v):
    """Convert old 5-pair format [[0,30],[30,50],...] to 4-boundary format [30,50,75,100]."""
    if v and isinstance(v[0], (list, tuple)):
        return [pair[0] for pair in v[1:]]
    return v


def _filter_known_keys(d: dict) -> dict:
    known = set(GameSettings.__dataclass_fields__)
    return {k: v for k, v in d.items() if k in known}

def load_settings() -> GameSettings:
    path = _settings_path()
    if not path.exists():
        return GameSettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        gs = GameSettings(**_filter_known_keys(raw))
        gs.outcome_directions = _normalize_directions(_coerce_keys(gs.outcome_directions))
        gs.fixed_thresholds = _migrate_fixed_thresholds(gs.fixed_thresholds)
        return gs
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        return GameSettings()


def save_settings(settings: GameSettings) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_dataclass_to_dict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _dataclass_to_dict(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return {f: _dataclass_to_dict(getattr(obj, f)) for f in obj.__dataclass_fields__}
    if isinstance(obj, dict):
        return {str(k): _dataclass_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_dataclass_to_dict(v) for v in obj]
    return obj


_game_settings: Optional[GameSettings] = None


def get_settings() -> GameSettings:
    global _game_settings
    if _game_settings is None:
        _game_settings = load_settings()
    return _game_settings


def update_settings(**kwargs) -> GameSettings:
    global _game_settings
    settings = get_settings()
    for key, value in kwargs.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)
    save_settings(settings)
    _game_settings = settings
    return settings


def reset_settings() -> GameSettings:
    global _game_settings
    gs = GameSettings()
    save_settings(gs)
    _game_settings = gs
    return gs
