import re

import bcrypt

from backend.app.core.constants import PASSWORD_MIN_LENGTH


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def validate_password(password: str) -> tuple[bool, str]:
    """checks the strength rules, returns (ok, message)"""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."

    missing = []
    if not re.search(r"[A-Z]", password):
        missing.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        missing.append("at least one lowercase letter")
    if not re.search(r"\d", password):
        missing.append("at least one number")
    if not re.search(r"[^A-Za-z0-9]", password):
        missing.append("at least one special character")

    if missing:
        return False, f"Password must contain {', '.join(missing)}."
    return True, "Password is valid."
