import math

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.providers.registry import registry
from backend.session import session_store
from backend.game_logic import (
    ScoringParams,
    Split,
    compute_outcome_tier,
    compute_speed_stats,
    compute_tier_boundaries,
    compute_weighted_avg,
    get_outcome_label,
    DEFAULT_AVG_CPM,
    DEFAULT_MIN_STDDEV_CPM,
)
from backend.prompt_engine import build_prompt, build_first_paragraph_prompt, parse_llm_response, sanitize_text, strip_thinking, validate_llm_response, NEUTRAL_FALLBACK
from backend.settings_manager import get_settings, build_scoring_params, GameSettings, _settings_path, save_settings
from backend.logger import logger

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None
    session_id: str | None = None
    splits: list[Split] | None = None


class GenerateResponse(BaseModel):
    response: str
    session_id: str
    outcome_tier: int
    outcome_label: str
    tier_boundaries: list[float]


def _compute_first_paragraph_tier(splits: list[Split], params: ScoringParams) -> int:
    n = len(splits)
    if n == 0:
        return 2
    baseline_count = math.ceil(n / 2)
    baseline = splits[:baseline_count]
    evaluated = splits[baseline_count:]
    if not evaluated:
        return 2
    avg, stddev = compute_speed_stats(baseline, params.min_stddev_cpm)
    evaluated_avg = compute_weighted_avg(evaluated)
    effective_stddev = stddev / math.sqrt(len(evaluated))
    return compute_outcome_tier(evaluated_avg, avg=avg, stddev=effective_stddev, params=params)


def _compute_subsequent_tier(splits: list[Split], rolling: list[Split], params: ScoringParams) -> int:
    if not splits:
        return 2
    avg, stddev = compute_speed_stats(rolling, params.min_stddev_cpm)
    paragraph_avg = compute_weighted_avg(splits)
    effective_stddev = stddev / math.sqrt(len(splits))
    return compute_outcome_tier(paragraph_avg, avg=avg, stddev=effective_stddev, params=params)


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(body: GenerateRequest):
    logger.info("POST /api/generate session_id=%s prompt_len=%d splits=%s",
                 body.session_id, len(body.prompt), body.splits)
    try:
        if body.session_id is None:
            session = session_store.create(initial_prompt=body.prompt)
            gs = get_settings()
            wrapped = build_first_paragraph_prompt(body.prompt, max_words=gs.paragraph_word_count)
            logger.debug("First paragraph prompt:\n%s", wrapped)
            raw_llm = await registry.generate(wrapped, body.model)
            text = sanitize_text(parse_llm_response(strip_thinking(raw_llm)))
            logger.debug("First paragraph raw=%r parsed=%r valid=%s", raw_llm, text, validate_llm_response(text))
            if not validate_llm_response(text):
                text = NEUTRAL_FALLBACK
                logger.warning("First paragraph invalid, using fallback")
            params = build_scoring_params(gs)
            bounds = compute_tier_boundaries(params=params)
            return GenerateResponse(
                response=text,
                session_id=session.id,
                outcome_tier=2,
                outcome_label="neutral",
                tier_boundaries=bounds,
            )

        session = session_store.get(body.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        gs = get_settings()
        params = build_scoring_params(gs)

        splits = body.splits or []
        rolling = session.rolling_window.to_list()

        bounds: list[float] = []
        if not rolling:
            outcome_tier = _compute_first_paragraph_tier(splits, params)
            n = len(splits)
            if n == 0:
                bounds = compute_tier_boundaries(params=params)
            elif n == 1:
                bounds = compute_tier_boundaries(avg=splits[0].speed_cpm, stddev=params.min_stddev_cpm, params=params)
            else:
                baseline_count = math.ceil(n / 2)
                baseline = splits[:baseline_count]
                avg, stddev = compute_speed_stats(baseline, params.min_stddev_cpm)
                bounds = compute_tier_boundaries(avg=avg, stddev=stddev, params=params)
            logger.debug("Outcome: first paragraph splits=%d rolling=[] -> tier=%d", len(splits), outcome_tier)
        else:
            outcome_tier = _compute_subsequent_tier(splits, rolling, params)
            avg, stddev = compute_speed_stats(rolling, params.min_stddev_cpm)
            effective_stddev = stddev / math.sqrt(len(splits)) if splits else stddev
            bounds = compute_tier_boundaries(avg=avg, stddev=effective_stddev, params=params)
            logger.debug("Outcome: subsequent splits=%d rolling=%d -> tier=%d", len(splits), len(rolling), outcome_tier)

        paragraph_cpm = compute_weighted_avg(splits)
        logger.debug("Append paragraph text_len=%d cpm=%.1f tier=%d splits=%d",
                     len(body.prompt), paragraph_cpm, outcome_tier, len(splits))

        session_store.append_paragraph(
            session_id=body.session_id,
            text=body.prompt,
            speed_cpm=paragraph_cpm,
            time_taken_ms=0,
            accuracy=1.0,
            outcome_tier=outcome_tier,
            splits=splits,
        )

        history_texts = [r.text for r in session.history]
        assembled = build_prompt(
            initial_context=session.initial_prompt,
            history=history_texts,
            outcome_tier=outcome_tier,
            outcome_directions=gs.outcome_directions,
            max_words=gs.paragraph_word_count,
        )
        logger.debug("LLM prompt:\n%s", assembled)
        raw = await registry.generate(assembled, body.model)
        next_text = sanitize_text(parse_llm_response(strip_thinking(raw)))
        logger.debug("LLM response raw=%r parsed=%r valid=%s", raw, next_text, validate_llm_response(next_text))
        if not validate_llm_response(next_text):
            if session.history:
                next_text = session.history[-1].text
                logger.warning("Invalid LLM response, falling back to last paragraph")
            else:
                next_text = NEUTRAL_FALLBACK
                logger.warning("Invalid LLM response, falling back to neutral fallback")

        return GenerateResponse(
            response=next_text,
            session_id=body.session_id,
            outcome_tier=outcome_tier,
            outcome_label=get_outcome_label(outcome_tier),
            tier_boundaries=bounds,
        )
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error("LLM request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {exc}",
        )


@router.get("/api/health")
async def health():
    path = _settings_path()
    first_visit = not path.exists()
    if first_visit:
        save_settings(GameSettings())
    ollama_running = await registry.is_available()
    return {"first_visit": first_visit, "ollama_running": ollama_running}
