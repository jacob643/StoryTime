from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from backend.game_logic import ScoringParams, DEFAULT_AVG_CPM, MAX_ROLLING_WINDOW
from backend.settings_manager import get_settings as _get_gs
from backend.logger import logger


@dataclass
class ParagraphRecord:
    text: str
    speed_cpm: float
    time_taken_ms: int
    accuracy: float
    outcome_tier: int
    split_speeds: list[float] = field(default_factory=list)


@dataclass
class GameSession:
    id: str
    created_at: datetime
    history: list[ParagraphRecord] = field(default_factory=list)
    initial_prompt: str = ""
    current_outcome_tier: int = 0
    rolling_splits: list[float] = field(default_factory=list)
    initial_avg_cpm: float = DEFAULT_AVG_CPM
    scoring_params: ScoringParams = field(default_factory=ScoringParams)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, GameSession] = {}

    def create(self, initial_prompt: str = "", initial_avg_cpm: float | None = None) -> GameSession:
        gs = _get_gs()
        params = ScoringParams(
            mode=gs.scoring_mode,
            min_data=gs.min_data,
            min_stddev_cpm=gs.min_stddev_cpm,
            tier_0_max_sigma=gs.tier_0_max_sigma,
            tier_1_max_sigma=gs.tier_1_max_sigma,
            tier_2_max_sigma=gs.tier_2_max_sigma,
            tier_3_max_sigma=gs.tier_3_max_sigma,
        )
        session = GameSession(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            initial_prompt=initial_prompt,
            initial_avg_cpm=initial_avg_cpm if initial_avg_cpm is not None else gs.default_avg_cpm,
            scoring_params=params,
        )
        self._sessions[session.id] = session
        logger.info("SessionStore.create id=%s initial_prompt=%s", session.id, initial_prompt)
        return session

    def get(self, session_id: str) -> Optional[GameSession]:
        return self._sessions.get(session_id)

    def append_paragraph(
        self,
        session_id: str,
        text: str,
        speed_cpm: float,
        time_taken_ms: int,
        accuracy: float,
        outcome_tier: int,
        split_speeds: list[float] | None = None,
    ) -> Optional[ParagraphRecord]:
        session = self.get(session_id)
        if session is None:
            return None
        record = ParagraphRecord(
            text=text,
            speed_cpm=speed_cpm,
            time_taken_ms=time_taken_ms,
            accuracy=accuracy,
            outcome_tier=outcome_tier,
            split_speeds=split_speeds or [],
        )
        session.history.append(record)
        if split_speeds:
            session.rolling_splits.extend(split_speeds)
            while len(session.rolling_splits) > MAX_ROLLING_WINDOW:
                session.rolling_splits.pop(0)
        logger.debug("SessionStore.append_paragraph session=%s entry=%d cpm=%.1f tier=%d rolling_len=%d",
                     session_id, len(session.history), speed_cpm, outcome_tier, len(session.rolling_splits))
        return record


session_store = SessionStore()
