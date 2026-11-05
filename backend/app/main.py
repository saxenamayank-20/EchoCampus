"""EchoCampus API.

Run from the repo root:
    alembic upgrade head                              # create / update the tables
    uvicorn backend.app.main:app --reload --port 8000
Swagger docs are at /docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from backend.app.agents.checkpointer import get_checkpointer
from backend.app.api.errors import register_error_handlers
from backend.app.api.routes import admin, attachments, auth, complaints, manager, meta, notifications, policies
from backend.app.core.config import settings
from backend.app.db.seed import seed_staff
from backend.app.db.session import SessionLocal
from backend.app.jobs.scheduler import start_scheduler


def create_app(run_startup: bool = True) -> FastAPI:
    """builds the app. tests pass run_startup=False so the real db is never touched"""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if run_startup:
            # tables come from alembic (alembic upgrade head), here we only add missing staff accounts
            try:
                with SessionLocal() as db:
                    seed_staff(db, settings.seed_passwords())
            except SQLAlchemyError as e:
                print(f"[STARTUP] couldn't seed staff, did you run 'alembic upgrade head'? ({type(e).__name__})")
            # langgraph's checkpoint tables, made here before any request has a transaction open
            # (its setup uses CREATE INDEX CONCURRENTLY, which waits for every open transaction)
            try:
                get_checkpointer()
            except Exception as e:
                print(f"[STARTUP] checkpointer not ready, closure graph will run step by step: {e}")
        scheduler = start_scheduler() if run_startup and settings.run_scheduler else None
        yield
        if scheduler:
            scheduler.shutdown(wait=False)

    app = FastAPI(title="EchoCampus API", version="0.2.0", lifespan=lifespan)

    # only our react app may call the api from a browser
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                       allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])
    register_error_handlers(app)

    for module in (auth, complaints, attachments, manager, admin, notifications, policies, meta):
        app.include_router(module.router)
    return app


app = create_app()
