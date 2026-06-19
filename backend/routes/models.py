from fastapi import APIRouter
from backend.providers.registry import registry

router = APIRouter()


@router.get("/api/models")
async def list_models():
    providers = await registry.discover()
    return {"providers": providers}
