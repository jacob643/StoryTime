from fastapi import APIRouter
from backend.performance_store import reset_performance
from backend.logger import logger

router = APIRouter()


@router.post("/api/performance/reset")
async def reset_performance_endpoint():
    logger.info("POST /api/performance/reset")
    reset_performance()
    return {"ok": True}
