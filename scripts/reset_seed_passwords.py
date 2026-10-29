"""Re-hash Admin/Manager passwords in the database from the values in .env.

Use this after changing ADMIN_SEED_PASSWORD / GM00x_PASSWORD in .env, because
seeding only creates accounts that do not exist yet.

Run from the repo root:  python scripts/reset_seed_passwords.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.config import settings
from backend.app.db.seed import reset_staff_passwords
from backend.app.db.session import SessionLocal, init_db


def main() -> int:
    """Ensure tables exist, then update staff passwords from .env."""
    init_db()
    with SessionLocal() as db:
        updated = reset_staff_passwords(db, settings.seed_passwords())
    print(f"[UPDATE] updated: {', '.join(updated) or 'nothing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
