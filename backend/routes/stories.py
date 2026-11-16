from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import httpx

from backend import story_file
from backend.game_logic import (
    compute_speed_stats,
    compute_tier_boundaries,
)
from backend.logger import logger
from backend.performance_store import load_performance
from backend.prompt_engine import (
    NEUTRAL_FALLBACK,
    build_prompt,
    parse_llm_response,
    sanitize_text,
    strip_thinking,
    validate_llm_response,
)
from backend.providers.registry import registry
from backend.session import session_store
from backend.settings_manager import build_scoring_params, get_settings

router = APIRouter()


class StoryListItem(BaseModel):
    story_id: str
    premise: str
    paragraph_count: int
    has_current: bool
    updated_at: str
    last_speed_cpm: float | None = None
    last_outcome_tier: int | None = None


class StoryListResponse(BaseModel):
    stories: list[StoryListItem]
    total: int


class StoryParagraphResponse(BaseModel):
    text: str
    speed_cpm: float | None = None
    outcome_tier: int | None = None
    completed_at: str | None = None


class StoryDetailResponse(BaseModel):
    story_id: str
    premise: str
    paragraphs: list[StoryParagraphResponse]
    current: str | None = None
    tier_boundaries: list[float]


class ResumeResponse(BaseModel):
    session_id: str
    story_id: str
    premise: str
    paragraphs: list[StoryParagraphResponse]
    current: str | None = None
    tier_boundaries: list[float]


class ContinueResponse(BaseModel):
    response: str
    outcome_tier: int
    tier_boundaries: list[float]


def _get_story_or_404(story_id: str) -> story_file.Story:
    try:
        story = story_file.load_story(story_id)
    except story_file.InvalidStoryId:
        raise HTTPException(status_code=404, detail="Story not found")
    except story_file.InvalidStoryFormat as exc:
        raise HTTPException(status_code=422, detail=f"Invalid story file: {exc}")
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


def _paragraphs(story: story_file.Story) -> list[StoryParagraphResponse]:
    return [
        StoryParagraphResponse(
            text=paragraph.text,
            speed_cpm=paragraph.speed_cpm,
            outcome_tier=paragraph.outcome_tier,
            completed_at=paragraph.completed_at.isoformat() if paragraph.completed_at else None,
        )
        for paragraph in story.paragraphs
    ]


def _boundaries_for_session(session, params) -> list[float]:
    splits = session.rolling_window.to_list()
    if splits:
        avg, stddev = compute_speed_stats(splits, params.min_stddev_cpm)
        return compute_tier_boundaries(avg=avg, stddev=stddev, params=params)
    return compute_tier_boundaries(params=params)


def _global_boundaries(params) -> list[float]:
    splits = load_performance()
    if splits:
        avg, stddev = compute_speed_stats(splits, params.min_stddev_cpm)
        return compute_tier_boundaries(avg=avg, stddev=stddev, params=params)
    return compute_tier_boundaries(params=params)


def _tone_tier(story: story_file.Story) -> int:
    if not story.paragraphs:
        return 2
    tier = story.paragraphs[-1].outcome_tier
    return tier if tier is not None else 2


@router.get("/api/stories", response_model=StoryListResponse)
async def list_stories_endpoint(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=500),
):
    summaries = story_file.list_stories()
    if q and q.strip():
        needle = q.strip().casefold()
        summaries = [s for s in summaries if needle in s.premise.casefold()]

    total = len(summaries)
    page = summaries[offset:offset + limit]
    return StoryListResponse(
        stories=[
            StoryListItem(
                story_id=summary.story_id,
                premise=summary.premise,
                paragraph_count=summary.paragraph_count,
                has_current=summary.has_current,
                updated_at=summary.updated_at.isoformat(),
                last_speed_cpm=summary.last_speed_cpm,
                last_outcome_tier=summary.last_outcome_tier,
            )
            for summary in page
        ],
        total=total,
    )


@router.get("/api/stories/{story_id}", response_model=StoryDetailResponse)
async def get_story_endpoint(story_id: str):
    story = _get_story_or_404(story_id)
    params = build_scoring_params(get_settings())
    return StoryDetailResponse(
        story_id=story.story_id,
        premise=story.premise,
        paragraphs=_paragraphs(story),
        current=story.current,
        tier_boundaries=_global_boundaries(params),
    )


@router.post("/api/stories/{story_id}/resume", response_model=ResumeResponse)
async def resume_story_endpoint(story_id: str):
    story = _get_story_or_404(story_id)
    session = session_store.get_live_by_story(story.story_id)
    if session is None:
        session = session_store.resume(story)
    else:
        session.story = story

    params = build_scoring_params(get_settings())
    logger.info(
        "POST /api/stories/%s/resume session=%s paragraphs=%d has_current=%s",
        story.story_id,
        session.id,
        len(session.history),
        story.current is not None,
    )
    return ResumeResponse(
        session_id=session.id,
        story_id=story.story_id,
        premise=story.premise,
        paragraphs=_paragraphs(story),
        current=story.current,
        tier_boundaries=_boundaries_for_session(session, params),
    )


@router.post("/api/stories/{story_id}/continue", response_model=ContinueResponse)
async def continue_story_endpoint(story_id: str):
    story = _get_story_or_404(story_id)
    session = session_store.get_live_by_story(story.story_id)
    if session is None:
        session = session_store.resume(story)

    params = build_scoring_params(get_settings())
    bounds = _boundaries_for_session(session, params)
    outcome_tier = _tone_tier(story)

    if story.current is not None:
        return ContinueResponse(
            response=story.current,
            outcome_tier=outcome_tier,
            tier_boundaries=bounds,
        )

    gs = get_settings()
    history_texts = [paragraph.text for paragraph in story.paragraphs]
    assembled = build_prompt(
        initial_context=story.premise,
        history=history_texts,
        outcome_tier=outcome_tier,
        outcome_directions=gs.outcome_directions,
        max_words=gs.paragraph_word_count,
        template=gs.continuation_prompt_template,
    )
    logger.debug("Continue story %s prompt:\n%s", story.story_id, assembled)

    try:
        raw = await registry.generate(assembled)
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error("Continue story LLM failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"LLM provider error: {exc}")

    next_text = sanitize_text(parse_llm_response(strip_thinking(raw)))
    if not validate_llm_response(next_text):
        next_text = history_texts[-1] if history_texts else NEUTRAL_FALLBACK
        logger.warning("Invalid continuation response, using fallback")

    try:
        story_file.append_paragraph(story, next_text)
    except (OSError, ValueError) as exc:
        logger.exception("Could not append continuation for story %s", story.story_id)
        raise HTTPException(status_code=500, detail=f"Could not save story: {exc}")

    return ContinueResponse(
        response=next_text,
        outcome_tier=outcome_tier,
        tier_boundaries=bounds,
    )
