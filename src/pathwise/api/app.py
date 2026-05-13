from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pathwise.api import (
    auth,
    chat,
    checkins,
    docs,
    plans,
    profile,
    questionnaire,
    seasons,
)
from pathwise.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    settings.users_dir.mkdir(parents=True, exist_ok=True)
    settings.otp_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Pathwise", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(profile.router)
    app.include_router(seasons.router)
    app.include_router(questionnaire.router)
    app.include_router(plans.router)
    app.include_router(chat.router)
    app.include_router(checkins.router)
    app.include_router(docs.router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()
