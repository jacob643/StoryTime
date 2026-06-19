from fastapi import APIRouter
from pydantic import BaseModel
from backend.providers.ollama import OllamaProvider

router = APIRouter()
provider = OllamaProvider()


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None


class GenerateResponse(BaseModel):
    response: str


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(body: GenerateRequest):
    text = await provider.generate(body.prompt, body.model)
    return GenerateResponse(response=text)


@router.get("/api/health")
async def health():
    available = await provider.is_available()
    return {"ollama_available": available}
