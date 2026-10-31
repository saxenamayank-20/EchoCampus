from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
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
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_downgrade_to_nothing_and_back(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = alembic_cfg(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert inspect(create_engine(url)).get_table_names() == ["alembic_version"]
    command.upgrade(cfg, "head")
