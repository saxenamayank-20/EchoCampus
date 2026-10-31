from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.db.base import Base


def normalize_url(url: str) -> str:
    """neon gives postgresql://..., tell sqlalchemy to use the psycopg (v3) driver"""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str) -> Engine:
    url = normalize_url(url)
    if not url.startswith("sqlite"):
        # neon sleeps when idle and drops old connections: pre_ping tests a connection before use.
        # prepare_threshold=None: no prepared statements, the neon pooler (pgbouncer) can't share them
        return create_engine(url, pool_pre_ping=True, pool_recycle=300,
                             connect_args={"prepare_threshold": None})

    engine = create_engine(url, connect_args={"check_same_thread": False})

    # sqlite ignores foreign keys unless we switch them on
    @event.listens_for(engine, "connect")
    def _foreign_keys_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(bind: Engine = engine) -> None:
    """create all tables straight from the models. only tests use this now, the real db uses alembic"""
    from backend.app import models  # noqa: F401  loads the model classes so their tables are known

    Base.metadata.create_all(bind)
