import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.app.core.config import settings
from backend.app.core.constants import PASSWORD_MIN_LENGTH

JWT_ALGORITHM = "HS256"
# no secret in .env = random per run, so tokens die on restart (ok for dev only)
JWT_SECRET = settings.jwt_secret or secrets.token_urlsafe(32)


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


def create_access_token(user_id: str, role: str) -> str:
    """signed token with who you are (sub), your role and when it runs out (exp)"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "role": role, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """raises jwt.PyJWTError if the token is fake, changed or expired"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
