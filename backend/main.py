import sys
import uvicorn
import webbrowser
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.logger import logger
from backend.routes.generate import router as generate_router
from backend.routes.restart import router as restart_router
from backend.routes.simulate import router as simulate_router
from backend.routes.settings import router as settings_router
from backend.routes.models import router as models_router

app = FastAPI(title="Story Time")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    for err in exc.errors():
        logger.error(
            "Validation error: loc=%s msg=%s input=%s",
            ".".join(str(p) for p in err.get("loc", [])),
            err.get("msg"),
            err.get("input"),
        )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
app.include_router(generate_router)
app.include_router(restart_router)
app.include_router(simulate_router)
app.include_router(settings_router)
app.include_router(models_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


def main():
    print("+------------------------------------+", flush=True)
    print("|      Story Time v0.1.0             |", flush=True)
    print(f"|  http://{settings.host}:{settings.port}             |", flush=True)
    print("+------------------------------------+", flush=True)
    webbrowser.open(f"http://{settings.host}:{settings.port}")
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
