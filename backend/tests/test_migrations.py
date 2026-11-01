from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine, inspect

from backend.app import models  # noqa: F401
from backend.app.db.base import Base


def alembic_cfg(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.attributes["url"] = url
    return cfg


def test_upgrade_creates_every_table(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    command.upgrade(alembic_cfg(url), "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert set(Base.metadata.tables) <= tables


def test_migrations_match_the_models(tmp_path):
    """if someone changes a model but forgets a migration, this fails"""
    url = f"sqlite:///{tmp_path / 'm.db'}"
    command.upgrade(alembic_cfg(url), "head")
    with create_engine(url).connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": _compare_type})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == []


def _compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    # sqlite has no vector type and reads VECTOR(768) back as a number column. postgres stores it for real
    if isinstance(metadata_type, Vector):
        return False
    return None   # None = use alembic's normal comparison


def test_downgrade_to_nothing_and_back(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = alembic_cfg(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert inspect(create_engine(url)).get_table_names() == ["alembic_version"]
    command.upgrade(cfg, "head")


def test_0004_renames_old_ids(tmp_path):
    from sqlalchemy import text
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = alembic_cfg(url)
    command.upgrade(cfg, "0003")
    engine = create_engine(url)
    with engine.begin() as conn:
        for uid, email, role in [("ADMIN001", "a@x.edu", "admin"), ("GM002", "g@x.edu", "grievance_manager"),
                                 ("ST000105", "s@x.edu", "student")]:
            conn.execute(text("INSERT INTO users (user_id, name, email, password_hash, role, is_verified, is_active, "
                              "created_at) VALUES (:u, 'x', :e, 'h', :r, 1, 1, CURRENT_TIMESTAMP)"),
                         {"u": uid, "e": email, "r": role})
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert sorted(conn.scalars(text("SELECT user_id FROM users"))) == ["AD100", "GM102", "ST105"]
