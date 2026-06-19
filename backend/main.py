import sys
import uvicorn
import webbrowser
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.routes.generate import router as generate_router
from backend.routes.restart import router as restart_router

app = FastAPI(title="Story Time")
app.include_router(generate_router)
app.include_router(restart_router)

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
