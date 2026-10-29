"""Create the tables and the admin/manager accounts.

Run from the repo root:  python scripts/seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.config import settings
from backend.app.db.seed import seed_staff
from backend.app.db.session import SessionLocal, init_db


def main() -> int:
    init_db()
    with SessionLocal() as db:
        created = seed_staff(db, settings.seed_passwords())
    print(f"[SEED] created: {', '.join(created) or 'nothing new'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
