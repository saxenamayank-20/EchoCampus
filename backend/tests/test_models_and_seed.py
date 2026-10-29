import re
from pathlib import Path

from sqlalchemy import func, inspect, select

from backend.app.core.config import Settings
from backend.app.core.constants import CATEGORY_MANAGER_MAP
from backend.app.core.enums import Role
from backend.app.core.security import verify_password
from backend.app.db.seed import reset_staff_passwords, seed_staff
from backend.app.models import ManagerCategory, User
from backend.tests.conftest import STAFF_IDS, TEST_PASSWORD


def test_all_tables_are_created(db):
    tables = set(inspect(db.get_bind()).get_table_names())
    assert {"users", "manager_categories", "complaints", "complaint_history",
            "manager_updates", "email_otps"} <= tables


def test_seed_creates_staff_and_categories(seeded_db):
    users = seeded_db.scalars(select(User)).all()
    assert sorted(u.user_id for u in users) == sorted(STAFF_IDS)
    assert seeded_db.scalar(select(User).where(User.user_id == "ADMIN001")).role == Role.ADMIN
    assert seeded_db.scalar(select(func.count()).select_from(ManagerCategory)) == len(CATEGORY_MANAGER_MAP)


def test_seed_stores_hash_not_password(seeded_db):
    admin = seeded_db.scalar(select(User).where(User.user_id == "ADMIN001"))
    assert admin.password_hash != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, admin.password_hash)


def test_seed_skips_accounts_without_password(db):
    created = seed_staff(db, {"ADMIN001": TEST_PASSWORD, "GM001": ""})
    assert created == ["ADMIN001"]
    assert db.scalar(select(User).where(User.user_id == "GM001")) is None


def test_seed_twice_does_not_duplicate(seeded_db):
    again = seed_staff(seeded_db, {uid: TEST_PASSWORD for uid in STAFF_IDS})
    assert again == []
    assert seeded_db.scalar(select(func.count()).select_from(User)) == len(STAFF_IDS)


def test_reset_staff_passwords(seeded_db):
    reset_staff_passwords(seeded_db, {"GM001": "New@Pass99"})
    gm = seeded_db.scalar(select(User).where(User.user_id == "GM001"))
    assert verify_password("New@Pass99", gm.password_hash)


def test_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("GM002_PASSWORD", "FromEnv@1")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./other.db")
    s = Settings(_env_file=None)
    assert s.seed_passwords()["GM002"] == "FromEnv@1"
    assert s.database_url == "sqlite:///./other.db"


def test_settings_default_to_empty_and_local_sqlite(monkeypatch):
    for var in ["DATABASE_URL", "ADMIN_SEED_PASSWORD", "GM001_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.database_url.startswith("sqlite")
    assert s.seed_passwords()["ADMIN001"] == ""


def test_no_password_literals_in_backend_code():
    core = Path(__file__).parents[1] / "app"
    for path in core.rglob("*.py"):
        assert not re.search(r'_password\s*:\s*str\s*=\s*"[^"]+"', path.read_text()), path
