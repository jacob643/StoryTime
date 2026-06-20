import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.providers.registry import registry
from backend.session import session_store
from backend.settings_manager import get_settings
from backend.prompt_engine import build_first_paragraph_prompt, parse_llm_response, validate_llm_response, NEUTRAL_FALLBACK
from backend.logger import logger

router = APIRouter()


class RestartRequest(BaseModel):
    initial_prompt: str


class RestartResponse(BaseModel):
    response: str
    session_id: str
    outcome_tier: int
    outcome_label: str


@router.post("/api/restart", response_model=RestartResponse)
async def restart(body: RestartRequest):
    logger.info("POST /api/restart initial_prompt=%s", body.initial_prompt)
    try:
        session = session_store.create(initial_prompt=body.initial_prompt)
        prompt = build_first_paragraph_prompt(body.initial_prompt)
        logger.debug("Restart prompt:\n%s", prompt)
        raw = await registry.generate(prompt)
        text = parse_llm_response(raw)
        logger.debug("Restart raw=%r parsed=%r valid=%s", raw, text, validate_llm_response(text))
        if not validate_llm_response(text):
            text = NEUTRAL_FALLBACK
            logger.warning("Restart response invalid, using fallback")
        return RestartResponse(
            response=text,
            session_id=session.id,
            outcome_tier=2,
            outcome_label="neutral",
        )
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error("Restart LLM failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {exc}",
        )
