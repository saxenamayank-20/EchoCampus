from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.constants import CATEGORY_MANAGER_MAP, STAFF_ACCOUNTS
from backend.app.core.enums import Role
from backend.app.core.security import hash_password
from backend.app.models import ManagerCategory, User


def seed_staff(db: Session, passwords: dict[str, str]) -> list[str]:
    """create admin + managers + their categories if missing. returns the ids it created"""
    created = []
    for account in STAFF_ACCOUNTS:
        uid = account["user_id"]
        password = passwords.get(uid, "")
        if not password:
            print(f"[SEED] Skipping {uid}: no seed password set in .env")
            continue
        if db.scalar(select(User).where(User.user_id == uid)):
            continue
        db.add(User(**account, password_hash=hash_password(password), is_verified=True))
        created.append(uid)
    db.flush()

    for category, uid in CATEGORY_MANAGER_MAP.items():
        manager = db.scalar(select(User).where(User.user_id == uid))
        exists = db.scalar(select(ManagerCategory).where(ManagerCategory.category == category))
        if manager and not exists:
            db.add(ManagerCategory(manager_id=manager.id, category=category))

    db.commit()
    return created


def reset_staff_passwords(db: Session, passwords: dict[str, str]) -> list[str]:
    """re-hash staff passwords from .env, for when they change after the first seed"""
    updated = []
    for uid, password in passwords.items():
        if not password:
            print(f"[UPDATE] Skipping {uid}: no seed password set in .env")
            continue
        user = db.scalar(select(User).where(User.user_id == uid, User.role != Role.STUDENT))
        if user:
            user.password_hash = hash_password(password)
            updated.append(uid)
    db.commit()
    return updated
