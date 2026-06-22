import argparse
import os
import sys
import threading
import uvicorn
import webbrowser
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend._version import __version__
from backend.config import settings
from backend.logger import logger, set_verbose
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

_frontend_dir = os.path.join(sys._MEIPASS, "frontend") if getattr(sys, "frozen", False) else "frontend"
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="storytime", description="Story Time typing game")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    parser.add_argument("--no-reload", action="store_true", help="disable auto-reload (production)")
    args = parser.parse_args(argv)

    if args.version:
        print(f"Story Time v{__version__}")
        return

    if args.verbose:
        set_verbose()

    reload_enabled = not args.no_reload and not getattr(sys, "frozen", False)

    print("+------------------------------------+", flush=True)
    print(f"|      Story Time v{__version__}             |", flush=True)
    print(f"|  http://{settings.host}:{settings.port}             |", flush=True)
    print("+------------------------------------+", flush=True)
    threading.Timer(
        1.5,
        lambda: webbrowser.open(f"http://{settings.host}:{settings.port}"),
    ).start()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=reload_enabled,
        log_level="debug" if args.verbose else "info",
    )


if __name__ == "__main__":
    main()
