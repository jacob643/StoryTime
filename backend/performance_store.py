from __future__ import annotations

import json
from pathlib import Path
from typing import List

from backend.game_logic import Split
from backend.logger import logger

PERFORMANCE_PATH = Path.home() / ".storytime" / "performance.json"


def _split_from_dict(d: dict) -> Split:
    return Split(speed_cpm=float(d["speed_cpm"]), char_count=int(d["char_count"]))


def _split_to_dict(s: Split) -> dict:
    return {"speed_cpm": s.speed_cpm, "char_count": s.char_count}


def load_performance() -> list[Split]:
    try:
        if not PERFORMANCE_PATH.exists():
            return []
        raw = json.loads(PERFORMANCE_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            logger.warning("performance.json is not a list, ignoring")
            return []
        return [_split_from_dict(d) for d in raw]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError) as e:
        logger.warning("Could not load performance data: %s", e)
        return []


def save_performance(splits: list[Split]) -> None:
    try:
        PERFORMANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = [_split_to_dict(s) for s in splits]
        PERFORMANCE_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        logger.error("Could not save performance data: %s", e)


def reset_performance() -> None:
    try:
        if PERFORMANCE_PATH.exists():
            PERFORMANCE_PATH.unlink()
    except OSError as e:
        logger.error("Could not reset performance data: %s", e)
