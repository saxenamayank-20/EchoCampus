import bcrypt
import pytest
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.seed import seed_staff
from backend.app.db.session import init_db, make_engine

TEST_PASSWORD = "Test@1234"
STAFF_IDS = ["ADMIN001", "GM001", "GM002", "GM003", "GM004"]


@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    # bcrypt is slow on purpose, the lowest cost keeps tests quick
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, "gensalt", lambda: real_gensalt(rounds=4))


@pytest.fixture
def db(tmp_path) -> Session:
    """fresh sqlite file per test, so tests never touch the real db"""
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_db(db) -> Session:
    seed_staff(db, {uid: TEST_PASSWORD for uid in STAFF_IDS})
    return db
