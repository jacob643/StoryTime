from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from backend.game_logic import Split, ScoringParams, DEFAULT_AVG_CPM, ROLLING_MAX_CHARS
from backend.performance_store import load_performance
from backend.settings_manager import get_settings as _get_gs, build_scoring_params
from backend.story_file import Story
from backend.logger import logger


@dataclass
class RollingWindow:
    splits: deque[Split] = field(default_factory=deque)
    total_chars: int = 0
    max_chars: int = ROLLING_MAX_CHARS

    def add(self, split: Split) -> None:
        self.splits.append(split)
        self.total_chars += split.char_count
        while self.total_chars > self.max_chars and self.splits:
            oldest = self.splits.popleft()
            self.total_chars -= oldest.char_count

    def add_many(self, splits: list[Split]) -> None:
        for s in splits:
            self.add(s)

    def to_list(self) -> list[Split]:
        return list(self.splits)

    def __len__(self) -> int:
        return len(self.splits)

    def __bool__(self) -> bool:
        return len(self.splits) > 0


@dataclass
class ParagraphRecord:
    text: str
    speed_cpm: float
    time_taken_ms: int
    accuracy: float
    outcome_tier: int
    splits: list[Split] = field(default_factory=list)


@dataclass
class GameSession:
    id: str
    created_at: datetime
    history: list[ParagraphRecord] = field(default_factory=list)
    initial_prompt: str = ""
    current_outcome_tier: int = 0
    rolling_window: RollingWindow = field(default_factory=RollingWindow)
    initial_avg_cpm: float = DEFAULT_AVG_CPM
    scoring_params: ScoringParams = field(default_factory=ScoringParams)
    story_id: str | None = None
    story: Story | None = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, GameSession] = {}
        self._live_by_story: Dict[str, str] = {}

    def create(self, initial_prompt: str = "", initial_avg_cpm: float | None = None) -> GameSession:
        gs = _get_gs()
        params = build_scoring_params(gs)
        session = GameSession(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            initial_prompt=initial_prompt,
            initial_avg_cpm=initial_avg_cpm if initial_avg_cpm is not None else DEFAULT_AVG_CPM,
            scoring_params=params,
        )
        persisted = load_performance()
        if persisted:
            session.rolling_window.add_many(persisted)
            logger.info("SessionStore.create id=%s seeded rolling window with %d splits",
                        session.id, len(persisted))
        self._sessions[session.id] = session
        logger.info("SessionStore.create id=%s initial_prompt=%s", session.id, initial_prompt)
        return session

    def get(self, session_id: str) -> Optional[GameSession]:
        return self._sessions.get(session_id)

    def attach_story(self, session: GameSession, story: Story) -> GameSession:
        session.story = story
        session.story_id = story.story_id
        self._live_by_story[story.story_id] = session.id
        return session

    def get_live_by_story(self, story_id: str) -> Optional[GameSession]:
        session_id = self._live_by_story.get(story_id)
        if session_id is None:
            return None
        session = self._sessions.get(session_id)
        if session is None:
            self._live_by_story.pop(story_id, None)
        return session

    def discard_story(self, story_id: str) -> None:
        """Detach a live session after its story file is deleted."""
        session_id = self._live_by_story.pop(story_id, None)
        if session_id is None:
            return
        session = self._sessions.get(session_id)
        if session is not None and session.story_id == story_id:
            session.story_id = None
            session.story = None
        logger.info("Detached live session %s from deleted story %s", session_id, story_id)

    def resume(self, story: Story) -> GameSession:
        """Create a live session from a parsed story, reusing an existing one."""
        existing = self.get_live_by_story(story.story_id)
        if existing is not None:
            return existing

        session = self.create(initial_prompt=story.premise)
        self.attach_story(session, story)
        session.history = [
            ParagraphRecord(
                text=paragraph.text,
                speed_cpm=paragraph.speed_cpm if paragraph.speed_cpm is not None else 0.0,
                time_taken_ms=0,
                accuracy=1.0,
                outcome_tier=paragraph.outcome_tier if paragraph.outcome_tier is not None else 2,
            )
            for paragraph in story.paragraphs
        ]
        logger.info(
            "SessionStore.resume id=%s story=%s paragraphs=%d has_current=%s",
            session.id,
            story.story_id,
            len(session.history),
            story.current is not None,
        )
        return session

    def append_paragraph(
        self,
        session_id: str,
        text: str,
        speed_cpm: float,
        time_taken_ms: int,
        accuracy: float,
        outcome_tier: int,
        splits: list[Split] | None = None,
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
            splits=splits or [],
        )
        session.history.append(record)
        if splits:
            session.rolling_window.add_many(splits)
        logger.debug("SessionStore.append_paragraph session=%s entry=%d cpm=%.1f tier=%d rolling_chars=%d",
                     session_id, len(session.history), speed_cpm, outcome_tier, session.rolling_window.total_chars)
        return record


session_store = SessionStore()
