"""EchoCampus API.

Run from the repo root:  uvicorn backend.app.main:app --reload --port 8000
Swagger docs are at /docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.errors import register_error_handlers
from backend.app.api.routes import admin, attachments, auth, complaints, manager, meta
from backend.app.core.config import settings
from backend.app.db.seed import seed_staff
from backend.app.db.session import SessionLocal, init_db


def create_app(run_startup: bool = True) -> FastAPI:
    """builds the app. tests pass run_startup=False so the real db is never touched"""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if run_startup:
            init_db()
            with SessionLocal() as db:
                seed_staff(db, settings.seed_passwords())
        yield

    app = FastAPI(title="EchoCampus API", version="0.2.0", lifespan=lifespan)

    # only our react app may call the api from a browser
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                       allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])
    register_error_handlers(app)

    for module in (auth, complaints, attachments, manager, admin, meta):
        app.include_router(module.router)
    return app


app = create_app()
