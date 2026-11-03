"""Real postgres checks (enums, the student id sequence, ilike search).

Skipped unless TEST_DATABASE_URL is set. Everything runs inside a throwaway schema
that is dropped at the end, so the real tables are never touched. Use a direct
(non pooled) connection url, the neon pooler doesn't allow setting the schema.
"""
import os
import uuid
from urllib.parse import quote

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app import models  # noqa: F401  so Base knows every table
from backend.app.core.enums import Priority, Status
from backend.app.db.base import Base
from backend.app.db.seed import seed_staff
from backend.app.db.session import make_engine, normalize_url
from backend.app.repositories.complaint_repository import ComplaintFilters
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.user_service import UserService

BASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture(scope="module")
def pg_url():
    schema = f"test_{uuid.uuid4().hex[:8]}"
    admin_engine = create_engine(normalize_url(BASE_URL))
    with admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    # the test schema comes first, so every table is created and read there. public is last only so
    # the pgvector type (installed in public) is visible. alembic_version is pinned to the test
    # schema, otherwise alembic finds the real one in public and skips creating the tables
    sep = "&" if "?" in BASE_URL else "?"
    url = normalize_url(BASE_URL) + f"{sep}options={quote(f'-csearch_path={schema},public')}"
    cfg = Config("alembic.ini")
    cfg.attributes["url"] = url
    cfg.attributes["version_schema"] = schema
    command.upgrade(cfg, "head")
    with admin_engine.connect() as conn:
        here = set(conn.scalars(text("SELECT table_name FROM information_schema.tables WHERE table_schema = :s"),
                                {"s": schema}))
    missing = set(Base.metadata.tables) - here
    if missing:    # never let a test fall through to the real tables in public
        with admin_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        pytest.exit(f"test schema is missing tables {missing}, stopping before touching real data")
    yield url
    with admin_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin_engine.dispose()


@pytest.fixture
def pg(pg_url):
    engine = make_engine(pg_url)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    engine.dispose()


def test_runs_in_the_test_schema(pg):
    assert pg.scalar(text("SELECT current_schema()")).startswith("test_")
    assert pg.scalar(text("SELECT count(*) FROM alembic_version")) == 1


def test_enums_are_real_postgres_types(pg):
    for name in ("role", "status", "priority"):
        assert pg.scalar(text(f"SELECT typtype FROM pg_type WHERE oid = to_regtype('{name}')")) == "e"
    # a value outside the enum is refused by the database itself
    with pytest.raises(Exception):
        pg.execute(text("SELECT 'Done'::status"))
    pg.rollback()


def test_full_flow_on_postgres(pg):
    seed_staff(pg, {"AD100": "Test@1234", "GM102": "Test@1234", "GM103": "Test@1234"})
    users = UserService(pg)
    a = users.register_student("A", "a@college.edu", "Student@123", "MBA")
    b = users.register_student("B", "b@college.edu", "Student@123", "MBA")
    assert (a.user_id, b.user_id) == ("ST101", "ST102")   # from the sequence

    service = ComplaintService(pg)
    c = service.submit(a, "Ragging in hostel", "seniors troubling", "Ragging")
    assert c.priority == Priority.CRITICAL and c.status == Status.ASSIGNED

    items, total = service.search(a, ComplaintFilters(search="RAGGING"), 1, 10)   # ilike = any case
    assert total == 1 and items[0].ticket_id == c.ticket_id
    assert service.chart_stats()["by_status"] == {"Assigned": 1}


def test_vector_extension_available(pg):
    assert pg.scalar(text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")) == 1


def test_paused_closure_survives_a_restart(pg, pg_url, monkeypatch):
    """the closure graph pauses in postgres, a 'restart' (new saver + new session) resumes it"""
    from backend.app.agents.checkpointer import get_checkpointer, reset_checkpointer
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "database_url", pg_url)
    reset_checkpointer()
    pg.commit()
    get_checkpointer()      # creates its tables now, while no transaction of ours is open
    seed_staff(pg, {uid: "Test@1234" for uid in ("AD100", "GM102")})
    student = UserService(pg).register_student("Graph Test", "graph@college.edu", "Student@123", "MBA")
    service = ComplaintService(pg)
    gm = UserService(pg).get("GM102")
    c = service.submit(student, "Wifi slow", "library wifi is slow", "IT/Internet")
    service.update_status(c.ticket_id, "In Progress", gm)
    service.update_status(c.ticket_id, "Resolved", gm)
    service.request_close(c.ticket_id, gm, "New router installed")
    assert type(get_checkpointer()).__name__ == "PostgresSaver"
    assert pg.scalar(text("SELECT count(*) FROM checkpoints")) > 0   # saved in the test schema

    reset_checkpointer()                       # like a backend restart: nothing left in memory
    later = ComplaintService(pg)
    assert later.closure_state(c.ticket_id)["waiting_at"] == "await_student"
    later.student_respond(c.ticket_id, student, fixed=True, rating=4)
    assert later.closure_state(c.ticket_id)["waiting_at"] == "await_admin"
    reset_checkpointer()
