from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from backend.game_logic import ScoringParams, DEFAULT_AVG_CPM, MAX_ROLLING_WINDOW


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

    def create(self, initial_prompt: str = "", initial_avg_cpm: float = DEFAULT_AVG_CPM) -> GameSession:
        session = GameSession(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            initial_prompt=initial_prompt,
            initial_avg_cpm=initial_avg_cpm,
        )
        self._sessions[session.id] = session
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
        return record


session_store = SessionStore()
