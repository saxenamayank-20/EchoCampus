"""Re-hash Admin/Manager passwords in the local database from the values in .env.

Use this after changing ADMIN_SEED_PASSWORD / GM00x_PASSWORD in .env, because
seeding only creates accounts that do not exist yet.

Run from the repo root:  python scripts/reset_seed_passwords.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import init_db, update_predefined_user_passwords


def main() -> int:
    """Ensure tables exist, then update predefined users' passwords from .env."""
    init_db()
    ok, _ = update_predefined_user_passwords()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
