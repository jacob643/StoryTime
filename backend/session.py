from __future__ import annotations

import re
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from backend.game_logic import Split, ScoringParams, DEFAULT_AVG_CPM, ROLLING_MAX_CHARS, get_outcome_label
from backend.settings_manager import get_settings as _get_gs, build_scoring_params
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


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, GameSession] = {}

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
        self._sessions[session.id] = session
        logger.info("SessionStore.create id=%s initial_prompt=%s", session.id, initial_prompt)
        return session

    def get(self, session_id: str) -> Optional[GameSession]:
        return self._sessions.get(session_id)

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
        slug = re.sub(r'[\s-]+', '_', slug)
        return slug.strip('_')[:50]

    def _persist_paragraph(self, session: GameSession, record: ParagraphRecord) -> None:
        if not record.text.strip():
            return
        out_dir = Path.cwd() / "writtenStories"
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = self._slugify(session.initial_prompt) or "untitled"
        file_path = out_dir / f"{slug}_{session.id[:8]}.txt"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- Paragraph {len(session.history)} ---\n")
            f.write(f"Date: {now}\n")
            f.write(f"Speed: {record.speed_cpm:.1f} CPM | "
                    f"Tier: {record.outcome_tier} ({get_outcome_label(record.outcome_tier)})\n")
            if record.splits:
                chunk_str = ', '.join(f'{s.speed_cpm:.1f}({s.char_count})' for s in record.splits)
                f.write(f"Splits: [{chunk_str}]\n")
            f.write(f"\n{record.text}\n")

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
        self._persist_paragraph(session, record)
        logger.debug("SessionStore.append_paragraph session=%s entry=%d cpm=%.1f tier=%d rolling_chars=%d",
                     session_id, len(session.history), speed_cpm, outcome_tier, session.rolling_window.total_chars)
        return record


session_store = SessionStore()
