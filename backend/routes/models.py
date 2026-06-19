from fastapi import APIRouter
from backend.providers.ollama import OllamaProvider

router = APIRouter()
provider = OllamaProvider()


@router.get("/api/models")
async def list_models():
    models = await provider.list_models()
    return {"models": models, "provider": "ollama"}
