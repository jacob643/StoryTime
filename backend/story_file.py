from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from backend.game_logic import get_outcome_label
from backend.logger import logger

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
STORY_SUFFIX = ".txt"

_STORY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,120}$")
_PREMISE_RE = re.compile(r"^Premise: (.+)$")
_DATE_RE = re.compile(r"^Date: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$")
_SPEED_RE = re.compile(r"^Speed: ([0-9]+(?:\.[0-9]+)?) CPM \| Tier: ([0-4]) \(([^)]*)\)$")
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9\s-]")
_SLUG_SPACE_RE = re.compile(r"[\s-]+")

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
_SUMMARY_CACHE: dict[Path, tuple[int, int, "StorySummary | None"]] = {}


class InvalidStoryId(ValueError):
    """Raised when a story id is missing, malformed, or escapes the stories directory."""


class InvalidStoryFormat(ValueError):
    """Raised when a story file does not match the expected format."""


@dataclass
class StoryParagraph:
    text: str
    speed_cpm: float | None = None
    outcome_tier: int | None = None
    completed_at: datetime | None = None

    @property
    def is_completed(self) -> bool:
        return (
            self.speed_cpm is not None
            or self.outcome_tier is not None
            or self.completed_at is not None
        )


@dataclass
class Story:
    story_id: str
    premise: str
    path: Path
    paragraphs: list[StoryParagraph] = field(default_factory=list)
    current: str | None = None


@dataclass
class StorySummary:
    story_id: str
    premise: str
    paragraph_count: int
    has_current: bool
    updated_at: datetime
    last_speed_cpm: float | None
    last_outcome_tier: int | None


def stories_dir() -> Path:
    return Path.cwd() / "writtenStories"


def story_path(story_id: str) -> Path:
    if not isinstance(story_id, str) or not _STORY_ID_RE.fullmatch(story_id):
        raise InvalidStoryId(f"Invalid story id: {story_id!r}")
    directory = stories_dir().resolve()
    path = (directory / f"{story_id}{STORY_SUFFIX}").resolve()
    if path.parent != directory:
        raise InvalidStoryId("Story path escapes the stories directory")
    return path


def _lock_for(story_id: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(story_id)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[story_id] = lock
        return lock


def _normalize_premise(premise: str) -> str:
    normalized = " ".join(premise.replace("\r", " ").replace("\n", " ").split())
    return normalized or "untitled"


def _slugify(premise: str) -> str:
    slug = _SLUG_STRIP_RE.sub("", premise.lower())
    slug = _SLUG_SPACE_RE.sub("_", slug).strip("_")
    return slug[:50]


def _new_story_id(premise: str) -> str:
    base = _slugify(premise) or "untitled"
    directory = stories_dir()
    for _ in range(20):
        candidate = f"{base}_{uuid.uuid4().hex[:8]}"
        if not (directory / f"{candidate}{STORY_SUFFIX}").exists():
            return candidate
    raise RuntimeError("Could not allocate a unique story id")


def _normalize_paragraph(text: str) -> str:
    return " ".join(str(text).replace("\r", " ").replace("\n", " ").split())


def _escape_paragraph(text: str) -> str:
    """Keep a paragraph line from being mistaken for metadata on re-read."""
    text = _normalize_paragraph(text)
    if _PREMISE_RE.match(text) or _DATE_RE.match(text) or _SPEED_RE.match(text):
        return " " + text
    return text


def _unescape_paragraph(text: str) -> str:
    if text.startswith(" "):
        candidate = text[1:]
        if (
            _PREMISE_RE.match(candidate)
            or _DATE_RE.match(candidate)
            or _SPEED_RE.match(candidate)
        ):
            return candidate
    return text


def _parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, DATE_FORMAT)


def parse_story_file(path: Path, story_id: str | None = None) -> Story:
    """Parse a story file and validate its structure.

    Raises ``InvalidStoryFormat`` when the file is not a well-formed v2 story.
    """
    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise InvalidStoryFormat(f"Could not read story file: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InvalidStoryFormat("Story file is not valid UTF-8") from exc

    lines = content.splitlines()
    first_idx = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_idx is None:
        raise InvalidStoryFormat("Story file is empty")

    premise_match = _PREMISE_RE.match(lines[first_idx].strip())
    if premise_match is None:
        raise InvalidStoryFormat("Missing 'Premise:' header")
    premise = premise_match.group(1).strip()
    if not premise:
        raise InvalidStoryFormat("Empty premise")

    story = Story(
        story_id=story_id or path.stem,
        premise=premise,
        path=path,
    )
    current: StoryParagraph | None = None

    def finalize(paragraph: StoryParagraph, is_last: bool) -> None:
        if paragraph.speed_cpm is None and paragraph.outcome_tier is None and paragraph.completed_at is None:
            if is_last:
                story.current = paragraph.text
            else:
                logger.warning(
                    "Story file %s has an uncompleted paragraph before the end; treating it as completed",
                    path,
                )
                paragraph.speed_cpm = 0.0
                paragraph.outcome_tier = 2
                story.paragraphs.append(paragraph)
            return
        if paragraph.speed_cpm is None:
            paragraph.speed_cpm = 0.0
        if paragraph.outcome_tier is None:
            paragraph.outcome_tier = 2
        story.paragraphs.append(paragraph)

    for line in lines[first_idx + 1:]:
        if not line.strip():
            continue

        date_match = _DATE_RE.match(line)
        if date_match is not None:
            if current is None:
                raise InvalidStoryFormat("Date line appears before any paragraph")
            current.completed_at = _parse_datetime(date_match.group(1))
            continue

        speed_match = _SPEED_RE.match(line)
        if speed_match is not None:
            if current is None:
                raise InvalidStoryFormat("Speed line appears before any paragraph")
            current.speed_cpm = float(speed_match.group(1))
            current.outcome_tier = int(speed_match.group(2))
            continue

        if current is not None:
            finalize(current, is_last=False)
        current = StoryParagraph(text=_unescape_paragraph(line))

    if current is not None:
        finalize(current, is_last=True)

    if not story.paragraphs and story.current is None:
        raise InvalidStoryFormat("Story contains no paragraphs")

    return story


def load_story(story_id: str) -> Story | None:
    path = story_path(story_id)
    if not path.exists():
        return None
    return parse_story_file(path, story_id=story_id)


def delete_story(story_id: str) -> bool:
    """Delete a story file. Returns False when it does not exist."""
    path = story_path(story_id)
    with _lock_for(story_id):
        try:
            path.unlink()
        except FileNotFoundError:
            _SUMMARY_CACHE.pop(path, None)
            return False
    _SUMMARY_CACHE.pop(path, None)
    logger.info("Deleted story file %s", path.name)
    return True


def create_story(
    premise: str,
    opening_text: str,
    story_id: str | None = None,
) -> Story:
    premise = _normalize_premise(premise)
    text = _escape_paragraph(opening_text)
    if not text:
        raise ValueError("Opening paragraph is empty")

    directory = stories_dir()
    directory.mkdir(parents=True, exist_ok=True)
    story_id = story_id or _new_story_id(premise)
    path = story_path(story_id)

    with _lock_for(story_id):
        path.write_text(
            f"Premise: {premise}\n\n{text}\n",
            encoding="utf-8",
        )

    logger.info("Created story file %s (%d chars)", path.name, len(text))
    return Story(
        story_id=story_id,
        premise=premise,
        path=path,
        paragraphs=[],
        current=text,
    )


def complete_current(
    story: Story,
    speed_cpm: float,
    outcome_tier: int,
    completed_at: datetime | None = None,
) -> StoryParagraph:
    """Append Date/Speed metadata underneath the current (unwritten) paragraph."""
    if story.current is None:
        raise ValueError("Story has no current paragraph to complete")

    when = completed_at or datetime.now()
    stamp = when.strftime(DATE_FORMAT)
    tier = max(0, min(4, int(outcome_tier)))
    speed = max(0.0, float(speed_cpm))

    with _lock_for(story.story_id):
        with open(story.path, "a", encoding="utf-8") as handle:
            handle.write(f"Date: {stamp}\n")
            handle.write(f"Speed: {speed:.1f} CPM | Tier: {tier} ({get_outcome_label(tier)})\n")

    record = StoryParagraph(
        text=story.current,
        speed_cpm=speed,
        outcome_tier=tier,
        completed_at=when,
    )
    story.paragraphs.append(record)
    story.current = None
    logger.debug(
        "Completed story %s paragraph %d at %.1f CPM (tier %d)",
        story.story_id,
        len(story.paragraphs),
        speed,
        tier,
    )
    return record


def append_paragraph(story: Story, text: str) -> str:
    """Append the next unwritten paragraph underneath the completed block."""
    if story.current is not None:
        raise ValueError("Story already has an unwritten paragraph")
    text = _escape_paragraph(text)
    if not text:
        raise ValueError("Paragraph is empty")

    with _lock_for(story.story_id):
        with open(story.path, "a", encoding="utf-8") as handle:
            handle.write(f"\n{text}\n")

    story.current = text
    logger.debug("Appended current paragraph to story %s", story.story_id)
    return text


def _summarize(story: Story, mtime: datetime) -> StorySummary:
    last = story.paragraphs[-1] if story.paragraphs else None
    return StorySummary(
        story_id=story.story_id,
        premise=story.premise,
        paragraph_count=len(story.paragraphs),
        has_current=story.current is not None,
        updated_at=mtime,
        last_speed_cpm=last.speed_cpm if last else None,
        last_outcome_tier=last.outcome_tier if last else None,
    )


def list_stories() -> list[StorySummary]:
    """Return summaries for every valid story file, newest first.

    Files written in the old format (no ``Premise:`` header) are ignored.
    """
    directory = stories_dir()
    if not directory.is_dir():
        return []

    summaries: list[StorySummary] = []
    for path in directory.glob(f"*{STORY_SUFFIX}"):
        try:
            stat = path.stat()
        except OSError:
            continue

        cached = _SUMMARY_CACHE.get(path)
        if cached is not None and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            summary = cached[2]
        else:
            try:
                story = parse_story_file(path, story_id=path.stem)
            except InvalidStoryFormat as exc:
                logger.warning("Skipping invalid story file %s: %s", path.name, exc)
                summary = None
            else:
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                summary = _summarize(story, mtime)
            _SUMMARY_CACHE[path] = (stat.st_mtime_ns, stat.st_size, summary)

        if summary is not None:
            summaries.append(summary)

    summaries.sort(key=lambda item: item.updated_at, reverse=True)
    return summaries


def clear_cache() -> None:
    """Clear the in-memory summary cache (used by tests)."""
    _SUMMARY_CACHE.clear()
