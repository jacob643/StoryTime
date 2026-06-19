import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.config import settings
from backend.providers.ollama import OllamaProvider
from backend.session import session_store
from backend.game_logic import compute_outcome_tier, compute_speed_stats, get_outcome_label
from backend.prompt_engine import build_prompt, parse_llm_response

router = APIRouter()
provider = OllamaProvider()


class SimulateRequest(BaseModel):
    session_id: str | None = None
    simulated_speed_cpm: float


class SimulateResponse(BaseModel):
    response: str
    outcome_tier: int
    outcome_label: str


@router.post("/api/simulate", response_model=SimulateResponse)
async def simulate(body: SimulateRequest):
    if not settings.dev_mode:
        raise HTTPException(status_code=403, detail="Dev mode is disabled")

    try:
        session = None
        if body.session_id is not None:
            session = session_store.get(body.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found")

        if session is not None and len(session.rolling_splits) >= session.scoring_params.min_data:
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
            prompt = build_prompt(
                initial_context=session.initial_prompt,
                history=history_texts,
                outcome_tier=outcome_tier,
            )
        else:
            outcome_tier = compute_outcome_tier(body.simulated_speed_cpm)
            initial = session.initial_prompt if session else ""
            history_texts = [r.text for r in session.history] if session else []
            prompt = build_prompt(
                initial_context=initial,
                history=history_texts,
                outcome_tier=outcome_tier,
            )

        raw = await provider.generate(prompt)
        next_text = parse_llm_response(raw)

        return SimulateResponse(
            response=next_text,
            outcome_tier=outcome_tier,
            outcome_label=get_outcome_label(outcome_tier),
        )
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {exc}",
        )
