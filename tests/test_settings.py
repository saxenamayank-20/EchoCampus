"""Stage 0 checks: seed passwords come from the environment, not from code."""
import importlib
import re
from pathlib import Path

import config.settings as settings

SEED_VARS = ["ADMIN_SEED_PASSWORD", "GM001_PASSWORD", "GM002_PASSWORD",
             "GM003_PASSWORD", "GM004_PASSWORD"]


def test_seed_passwords_read_from_env(monkeypatch):
    for i, var in enumerate(SEED_VARS):
        monkeypatch.setenv(var, f"Test@Pass{i}")
    reloaded = importlib.reload(settings)
    assert [u[3] for u in reloaded.PREDEFINED_USERS] == [f"Test@Pass{i}" for i in range(5)]


def test_seed_passwords_empty_when_unset(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    for var in SEED_VARS:
        monkeypatch.delenv(var, raising=False)
    reloaded = importlib.reload(settings)
    assert all(u[3] == "" for u in reloaded.PREDEFINED_USERS)


def test_no_password_literals_in_settings():
    source = Path(settings.__file__).read_text()
    assert not re.search(r'_PASSWORD\s*=\s*"[^"]+"', source)
