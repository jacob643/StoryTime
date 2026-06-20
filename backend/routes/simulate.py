import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.config import settings
from backend.providers.registry import registry
from backend.session import session_store
from backend.game_logic import compute_outcome_tier, compute_speed_stats, get_outcome_label
from backend.prompt_engine import build_prompt, parse_llm_response
from backend.settings_manager import get_settings
from backend.logger import logger

router = APIRouter()


class SimulateRequest(BaseModel):
    session_id: str | None = None
    simulated_speed_cpm: float


class SimulateResponse(BaseModel):
    response: str
    session_id: str | None = None
    outcome_tier: int
    outcome_label: str


@router.post("/api/simulate", response_model=SimulateResponse)
async def simulate(body: SimulateRequest):
    logger.info("POST /api/simulate session_id=%s simulated_speed=%.1f", body.session_id, body.simulated_speed_cpm)
    if not settings.dev_mode:
        raise HTTPException(status_code=403, detail="Dev mode is disabled")

    try:
        session = None
        if body.session_id is not None:
            session = session_store.get(body.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found")

        gs = get_settings()
        if session is not None and len(session.rolling_splits) > 0:
            avg, stddev = compute_speed_stats(
                session.rolling_splits,
                session.scoring_params.min_stddev_cpm,
            )
            outcome_tier = compute_outcome_tier(
                body.simulated_speed_cpm,
                avg=avg,
                stddev=stddev,
                params=session.scoring_params,
            )
            history_texts = [r.text for r in session.history]
            max_chars = gs.target_split_size * 4
            prompt = build_prompt(
                initial_context=session.initial_prompt,
                history=history_texts,
                outcome_tier=outcome_tier,
                outcome_directions=gs.outcome_directions,
                max_chars=max_chars,
            )
            logger.debug("Simulate adaptive: rolling=%s avg=%.1f stddev=%.1f -> tier=%d",
                         session.rolling_splits, avg, stddev, outcome_tier)
        else:
            outcome_tier = compute_outcome_tier(body.simulated_speed_cpm)
            initial = session.initial_prompt if session else ""
            history_texts = [r.text for r in session.history] if session else []
            max_chars = gs.target_split_size * 4
            prompt = build_prompt(
                initial_context=initial,
                history=history_texts,
                outcome_tier=outcome_tier,
                outcome_directions=gs.outcome_directions,
                max_chars=max_chars,
            )
            logger.debug("Simulate fixed: speed=%.1f -> tier=%d", body.simulated_speed_cpm, outcome_tier)

        logger.debug("Simulate prompt:\n%s", prompt)
        raw = await registry.generate(prompt)
        next_text = parse_llm_response(raw)
        logger.debug("Simulate raw=%r parsed=%r", raw, next_text)

        if session is not None:
            session_store.append_paragraph(
                session_id=session.id,
                text=history_texts[-1] if history_texts else "",
                speed_cpm=body.simulated_speed_cpm,
                time_taken_ms=0,
                accuracy=1.0,
                outcome_tier=outcome_tier,
            )
            logger.debug("Simulate appended history entry speed=%.1f tier=%d", body.simulated_speed_cpm, outcome_tier)

        return SimulateResponse(
            response=next_text,
            session_id=session.id if session else None,
            outcome_tier=outcome_tier,
            outcome_label=get_outcome_label(outcome_tier),
        )
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error("Simulate LLM failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {exc}",
        )
