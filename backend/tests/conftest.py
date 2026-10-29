import re

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.deps import get_db, get_email_sender
from backend.app.db.seed import seed_staff
from backend.app.db.session import init_db, make_engine
from backend.app.main import create_app

TEST_PASSWORD = "Test@1234"
STUDENT_PASSWORD = "Student@123"
STAFF_IDS = ["ADMIN001", "GM001", "GM002", "GM003", "GM004"]


@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    # bcrypt is slow on purpose, the lowest cost keeps tests quick
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, "gensalt", lambda: real_gensalt(rounds=4))


@pytest.fixture
def session_factory(tmp_path):
    """fresh sqlite file per test, so tests never touch the real db"""
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db(session_factory) -> Session:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db) -> Session:
    seed_staff(db, {uid: TEST_PASSWORD for uid in STAFF_IDS})
    return db


class FakeSender:
    """catches mails instead of sending them"""

    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to, subject, body):
        self.sent.append((to, subject, body))

    def last_code(self) -> str:
        return re.search(r"\d{6}", self.sent[-1][2]).group()


@pytest.fixture
def mailbox() -> FakeSender:
    return FakeSender()


@pytest.fixture
def client(session_factory, seeded_db, mailbox, tmp_path, monkeypatch) -> TestClient:
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))

    def test_db():
        with session_factory() as s:
            yield s

    app = create_app(run_startup=False)
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_email_sender] = lambda: mailbox
    with TestClient(app) as c:
        yield c


def login(client, user_id, password=TEST_PASSWORD) -> dict:
    """auth header for that user"""
    r = client.post("/auth/login", json={"user_id": user_id, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_student(client, mailbox, email="student1@college.edu") -> tuple[str, dict]:
    """register + verify + login, returns (student id, auth header)"""
    r = client.post("/auth/register", json={"name": "Priya", "email": email,
                                            "password": STUDENT_PASSWORD, "department": "MBA"})
    assert r.status_code == 201, r.text
    uid = r.json()["user_id"]
    r = client.post("/auth/verify-otp", json={"user_id": uid, "code": mailbox.last_code()})
    assert r.status_code == 200, r.text
    return uid, login(client, uid, STUDENT_PASSWORD)
