from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.db.base import Base


def make_engine(url: str) -> Engine:
    if not url.startswith("sqlite"):
        return create_engine(url)

    engine = create_engine(url, connect_args={"check_same_thread": False})

    # sqlite ignores foreign keys unless we switch them on
    @event.listens_for(engine, "connect")
    def _foreign_keys_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(bind: Engine = engine) -> None:
    """create all tables (alembic takes over in phase 3)"""
    from backend.app import models  # noqa: F401  loads the model classes so their tables are known

    Base.metadata.create_all(bind)
