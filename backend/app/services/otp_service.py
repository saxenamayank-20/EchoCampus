import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import hash_password, verify_password
from backend.app.db.base import now
from backend.app.models import EmailOtp, User
from backend.app.services.email_service import EmailSender
from backend.app.services.errors import ConflictError, InvalidInputError


class OtpService:
    def __init__(self, db: Session, sender: EmailSender):
        self.db = db
        self.sender = sender

    def send(self, user: User) -> None:
        """new 6 digit code, old unused ones stop working"""
        if user.is_verified:
            raise ConflictError("This account is already verified.")
        self.db.execute(update(EmailOtp).where(EmailOtp.user_id == user.id, EmailOtp.used.is_(False))
                        .values(used=True))

        code = f"{secrets.randbelow(1_000_000):06d}"
        self.db.add(EmailOtp(user_id=user.id, code_hash=hash_password(code),
                             expires_at=now() + timedelta(minutes=settings.otp_expire_minutes)))
        self.db.commit()
        self.sender.send(user.email, "Your EchoCampus verification code",
                         f"Your code is {code}. It expires in {settings.otp_expire_minutes} minutes.")

    def verify(self, user: User, code: str) -> None:
        if user.is_verified:
            return
        otp = self.db.scalar(select(EmailOtp)
                             .where(EmailOtp.user_id == user.id, EmailOtp.used.is_(False))
                             .order_by(EmailOtp.id.desc()))
        if not otp:
            raise InvalidInputError("No active code. Ask for a new one.")
        if otp.expires_at < now():
            raise InvalidInputError("This code has expired. Ask for a new one.")
        if otp.attempts >= settings.otp_max_attempts:
            raise InvalidInputError("Too many wrong tries. Ask for a new code.")

        otp.attempts += 1
        if not verify_password(code, otp.code_hash):
            self.db.commit()   # save the attempt count even though it failed
            left = settings.otp_max_attempts - otp.attempts
            raise InvalidInputError(f"Wrong code. {left} tries left.")

        otp.used = True
        user.is_verified = True
        self.db.commit()
