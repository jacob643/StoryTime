from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class ParagraphRecord:
    text: str
    speed_cpm: float
    time_taken_ms: int
    accuracy: float
    outcome_tier: int


@dataclass
class GameSession:
    id: str
    created_at: datetime
    history: list[ParagraphRecord] = field(default_factory=list)
    initial_prompt: str = ""
    current_outcome_tier: int = 0


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, GameSession] = {}

    def create(self, initial_prompt: str = "") -> GameSession:
        session = GameSession(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            initial_prompt=initial_prompt,
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
        )
        session.history.append(record)
        return record


session_store = SessionStore()
