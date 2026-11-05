import os
import re

# tests must never touch the real db, redis, email or ai from .env.
# DATABASE_URL is set before the app is imported (env vars beat .env).
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["RUN_SCHEDULER"] = "false"
# empty env values count as "not set" (env_ignore_empty), so switch these off on the settings object itself
from backend.app.core.config import settings as _settings  # noqa: E402

_settings.redis_url = ""            # in-memory cache
_settings.smtp_host = ""            # emails are only printed
_settings.gemini_api_key = ""       # no real ai calls, tests use a fake

import bcrypt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.ai.llm_client import DisabledClient, get_llm
from backend.app.core.deps import get_db, get_email_sender
from backend.app.db.seed import seed_staff
from backend.app.db.session import init_db, make_engine
from backend.app.main import create_app

TEST_PASSWORD = "Test@1234"
STUDENT_PASSWORD = "Student@123"
STAFF_IDS = ["AD100", "GM101", "GM102", "GM103", "GM104"]


@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    # bcrypt is slow on purpose, the lowest cost keeps tests quick
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, "gensalt", lambda: real_gensalt(rounds=4))


@pytest.fixture(autouse=True)
def clean_cache_and_limits(monkeypatch):
    """every test starts with an empty cache, and limits high enough not to get in the way"""
    from backend.app.agents.checkpointer import reset_checkpointer
    from backend.app.core.cache import get_cache
    from backend.app.core.config import settings
    get_cache().clear()
    reset_checkpointer()      # paused graphs from another test must not leak in (thread ids repeat)
    monkeypatch.setattr(settings, "rate_limit_complaints_per_hour", 1000)
    monkeypatch.setattr(settings, "rate_limit_logins_per_15_min", 1000)


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
    app.dependency_overrides[get_llm] = lambda: DisabledClient()   # ai tests swap in a fake
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


# ── fake ai for phase 4 tests ────────────────────────────────────────────────
import hashlib  # noqa: E402

import numpy as np  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from backend.app.ai.llm_client import LLMClient, LLMError  # noqa: E402

STOP = {"the", "a", "an", "is", "in", "on", "of", "and", "to", "my", "for", "since", "not", "it", "at", "i", "are", "be"}


def word_vector(text: str, dim: int = 768) -> list[float]:
    """stand-in embedding: shared words = similar vectors. drops the 'task: ... | query:' prefix"""
    text = text.split("query:", 1)[-1].split("text:", 1)[-1].lower()
    v = np.zeros(dim)
    for word in re.findall(r"[a-z0-9]+", text):
        if word not in STOP:
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % dim] += 1
    n = np.linalg.norm(v)
    return list(v / n) if n else list(v)


class FakeLLM(LLMClient):
    """answers[feature] = dict (or function of the prompt) returned as the json. fail=True = ai down"""
    model = "fake"

    def __init__(self, answers=None, fail=False):
        self.answers = answers or {}
        self.fail = fail
        self.calls: list[str] = []
        self.prompts: list[str] = []

    def generate_json(self, feature, prompt, schema):
        self.calls.append(feature)
        self.prompts.append(prompt)
        answer = self.answers.get(feature)
        if callable(answer):
            answer = answer(prompt)
        if self.fail or answer is None:
            raise LLMError("fake ai is down")
        try:
            return schema.model_validate(answer)
        except ValidationError as e:     # the real client turns bad json into LLMError too
            raise LLMError("bad shape") from e

    def embed(self, feature, texts):
        self.calls.append(feature)
        if self.fail:
            raise LLMError("fake ai is down")
        return [word_vector(t) for t in texts]


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def ai_client(client, fake_llm):
    """the api client, but with the fake ai switched on"""
    client.app.dependency_overrides[get_llm] = lambda: fake_llm
    return client
