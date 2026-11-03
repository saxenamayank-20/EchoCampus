"""Where paused graphs are saved. Neon (postgres) for real runs, memory for sqlite and tests."""
import threading

from langgraph.checkpoint.memory import InMemorySaver

from backend.app.core.config import settings

_saver = None
_lock = threading.Lock()


def get_checkpointer():
    global _saver
    with _lock:            # two requests at once must not both create it
        if _saver is None:
            url = settings.database_url
            if url.startswith(("postgresql", "postgres://")):
                _saver = _postgres_saver(url)
            else:
                # lost on restart. the service then does the step directly (same rules)
                _saver = InMemorySaver()
        return _saver


def _postgres_saver(url: str):
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    conninfo = url.replace("postgresql+psycopg://", "postgresql://")
    # PostgresSaver needs autocommit + dict rows. prepare_threshold=None for the neon pooler (like sqlalchemy).
    # check_connection tests a connection before use, neon drops idle ones
    pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True, check=ConnectionPool.check_connection,
                          kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row})
    saver = PostgresSaver(pool)
    saver.setup()          # creates its checkpoint tables the first time
    return saver


def reset_checkpointer() -> None:
    """tests: start with a fresh saver (and close the postgres pool if there was one)"""
    global _saver
    with _lock:
        pool = getattr(_saver, "conn", None)
        if pool is not None:
            pool.close()
        _saver = None
