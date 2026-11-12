from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, now
from backend.app.models.user import User


class EmailOtp(Base):
    """6 digit email code. only the hash is stored, like a password"""

    __tablename__ = "email_otps"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    code_hash: Mapped[str] = mapped_column(String(255))
    # verify = new account, recovery = forgot id, login = forgot password. a code only works for its own purpose
    purpose: Mapped[str] = mapped_column(String(20), default="verify", server_default="verify")
    expires_at: Mapped[datetime]
    attempts: Mapped[int] = mapped_column(default=0)
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)

    user: Mapped[User] = relationship()
