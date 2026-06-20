import math

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.providers.registry import registry
from backend.session import session_store
from backend.game_logic import (
    ScoringParams,
    compute_outcome_tier,
    compute_speed_stats,
    get_outcome_label,
    DEFAULT_AVG_CPM,
    DEFAULT_MIN_STDDEV_CPM,
)
from backend.prompt_engine import build_prompt, build_first_paragraph_prompt, parse_llm_response, validate_llm_response, NEUTRAL_FALLBACK
from backend.settings_manager import get_settings
from backend.logger import logger

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None
    session_id: str | None = None
    speed_cpm: float | None = None
    split_speeds: list[float] | None = None


class GenerateResponse(BaseModel):
    response: str
    session_id: str
    outcome_tier: int
    outcome_label: str


def _compute_first_paragraph_tier(split_speeds: list[float], params: ScoringParams) -> int:
    n = len(split_speeds)
    if n == 0:
        return 2
    if n == 1:
        return compute_outcome_tier(
            split_speeds[0],
            avg=DEFAULT_AVG_CPM,
            stddev=DEFAULT_MIN_STDDEV_CPM,
            params=params,
        )

    baseline_count = math.ceil(n / 2)
    baseline = split_speeds[:baseline_count]
    evaluated = split_speeds[baseline_count:]
    avg, stddev = compute_speed_stats(baseline, params.min_stddev_cpm)
    evaluated_avg = sum(evaluated) / len(evaluated)
    return compute_outcome_tier(evaluated_avg, avg=avg, stddev=stddev, params=params)


def _compute_subsequent_tier(split_speeds: list[float], rolling: list[float], params: ScoringParams) -> int:
    avg, stddev = compute_speed_stats(rolling, params.min_stddev_cpm)
    paragraph_cpm = sum(split_speeds) / len(split_speeds) if split_speeds else 0
    return compute_outcome_tier(paragraph_cpm, avg=avg, stddev=stddev, params=params)


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(body: GenerateRequest):
    logger.info("POST /api/generate session_id=%s prompt_len=%d split_speeds=%s",
                 body.session_id, len(body.prompt), body.split_speeds)
    try:
        if body.session_id is None:
            session = session_store.create(initial_prompt=body.prompt)
            wrapped = build_first_paragraph_prompt(body.prompt)
            logger.debug("First paragraph prompt:\n%s", wrapped)
            raw_llm = await registry.generate(wrapped, body.model)
            text = parse_llm_response(raw_llm)
            logger.debug("First paragraph raw=%r parsed=%r valid=%s", raw_llm, text, validate_llm_response(text))
            if not validate_llm_response(text):
                text = NEUTRAL_FALLBACK
                logger.warning("First paragraph invalid, using fallback")
            return GenerateResponse(
                response=text,
                session_id=session.id,
                outcome_tier=2,
                outcome_label="neutral",
            )

        session = session_store.get(body.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        split_speeds = body.split_speeds or []
        params = session.scoring_params
        rolling = session.rolling_splits

        if not split_speeds and body.speed_cpm is not None:
            outcome_tier = compute_outcome_tier(body.speed_cpm)
            logger.debug("Outcome: fixed speed=%.1f CPM -> tier=%d", body.speed_cpm, outcome_tier)
        elif not rolling:
            outcome_tier = _compute_first_paragraph_tier(split_speeds, params)
            logger.debug("Outcome: first paragraph splits=%s rolling=[] -> tier=%d", split_speeds, outcome_tier)
        else:
            outcome_tier = _compute_subsequent_tier(split_speeds, rolling, params)
            logger.debug("Outcome: subsequent splits=%s rolling=%s -> tier=%d", split_speeds, rolling, outcome_tier)

        paragraph_cpm = sum(split_speeds) / len(split_speeds) if split_speeds else (body.speed_cpm or 0.0)
        logger.debug("Append paragraph text_len=%d cpm=%.1f tier=%d splits=%s",
                     len(body.prompt), paragraph_cpm, outcome_tier, split_speeds)

        session_store.append_paragraph(
            session_id=body.session_id,
            text=body.prompt,
            speed_cpm=paragraph_cpm,
            time_taken_ms=0,
            accuracy=1.0,
            outcome_tier=outcome_tier,
            split_speeds=split_speeds,
        )

        history_texts = [r.text for r in session.history]
        gs = get_settings()
        assembled = build_prompt(
            initial_context=session.initial_prompt,
            history=history_texts,
            outcome_tier=outcome_tier,
            outcome_directions=gs.outcome_directions,
        )
        logger.debug("LLM prompt:\n%s", assembled)
        raw = await registry.generate(assembled, body.model)
        next_text = parse_llm_response(raw)
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
        )
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error("LLM request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {exc}",
        )


@router.get("/api/health")
async def health():
    available = await registry.is_available()
    return {"ollama_available": available}
