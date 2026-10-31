"""Create the admin/manager accounts from the passwords in .env.

Run from the repo root, after the tables exist:
    alembic upgrade head
    python scripts/seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.config import settings
from backend.app.db.seed import seed_staff
from backend.app.db.session import SessionLocal


def main() -> int:
    with SessionLocal() as db:
        created = seed_staff(db, settings.seed_passwords())
    print(f"[SEED] created: {', '.join(created) or 'nothing new'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
