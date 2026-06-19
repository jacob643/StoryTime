import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.providers.registry import registry
from backend.session import session_store
from backend.settings_manager import get_settings

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
    try:
        session = session_store.create(initial_prompt=body.initial_prompt)
        text = await registry.generate(body.initial_prompt)
        return RestartResponse(
            response=text,
            session_id=session.id,
            outcome_tier=2,
            outcome_label="neutral",
        )
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {exc}",
        )
