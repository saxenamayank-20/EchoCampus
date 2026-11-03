"""alembic runs this for every migration command (upgrade, downgrade, revision --autogenerate)"""
from logging.config import fileConfig

from alembic import context

from backend.app import models  # noqa: F401  loads every model so alembic sees all tables
from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import make_engine, normalize_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# what the database should look like, alembic compares the real db to this
target_metadata = Base.metadata


def url() -> str:
    # tests can pass their own url, otherwise DATABASE_URL from .env
    return config.attributes.get("url") or normalize_url(settings.database_url)


def run_migrations_offline() -> None:
    """--sql mode: print the sql instead of running it"""
    context.configure(url=url(), target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=url().startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()


def include_name(name, type_, parent_names) -> bool:
    # langgraph creates and owns its checkpoint tables, they aren't in our models
    return not (type_ == "table" and name and name.startswith("checkpoint"))


def run_migrations_online() -> None:
    engine = make_engine(url())
    with engine.connect() as connection:
        # sqlite can't ALTER most things, batch mode rebuilds the table instead.
        # version_schema: the postgres tests keep alembic_version inside their throwaway schema
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=connection.dialect.name == "sqlite", include_name=include_name,
                          version_table_schema=config.attributes.get("version_schema"))
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
