from __future__ import annotations

from fastapi import FastAPI

from .api.routes import router


def create_app() -> FastAPI:
    application = FastAPI(title="Eye Visionary", version="0.1.0")
    application.include_router(router)
    return application


app = create_app()
