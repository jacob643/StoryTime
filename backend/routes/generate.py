from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.providers.ollama import OllamaProvider
from backend.session import session_store
from backend.game_logic import compute_outcome_tier, get_outcome_label
from backend.prompt_engine import build_prompt, parse_llm_response

router = APIRouter()
provider = OllamaProvider()


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None
    session_id: str | None = None
    speed_cpm: float | None = None


class GenerateResponse(BaseModel):
    response: str
    session_id: str
    outcome_tier: int
    outcome_label: str


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(body: GenerateRequest):
    if body.session_id is None:
        session = session_store.create(initial_prompt=body.prompt)
        text = await provider.generate(body.prompt, body.model)
        return GenerateResponse(
            response=text,
            session_id=session.id,
            outcome_tier=2,
            outcome_label="neutral",
        )

    session = session_store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    speed = body.speed_cpm if body.speed_cpm is not None else 0.0
    outcome_tier = compute_outcome_tier(speed)

    session_store.append_paragraph(
        session_id=body.session_id,
        text=body.prompt,
        speed_cpm=speed,
        time_taken_ms=0,
        accuracy=1.0,
        outcome_tier=outcome_tier,
    )

    history_texts = [r.text for r in session.history]
    assembled = build_prompt(
        initial_context=session.initial_prompt,
        history=history_texts,
        outcome_tier=outcome_tier,
    )
    raw = await provider.generate(assembled, body.model)
    next_text = parse_llm_response(raw)

    return GenerateResponse(
        response=next_text,
        session_id=body.session_id,
        outcome_tier=outcome_tier,
        outcome_label=get_outcome_label(outcome_tier),
    )


@router.get("/api/health")
async def health():
    available = await provider.is_available()
    return {"ollama_available": available}
