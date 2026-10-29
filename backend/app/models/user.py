from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.enums import Role
from backend.app.db.base import Base, enum_column, now


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(20), unique=True)   # ST000101 / GM001 / ADMIN001
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_column(Role))
    department: Mapped[str | None] = mapped_column(String(100))
    is_verified: Mapped[bool] = mapped_column(default=False)        # email otp comes in phase 2
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=now)

    categories: Mapped[list["ManagerCategory"]] = relationship(back_populates="manager")

    def __repr__(self) -> str:
        return f"<User {self.user_id} {self.role}>"


class ManagerCategory(Base):
    """one row per category, says which manager owns it"""

    __tablename__ = "manager_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(50), unique=True)

    manager: Mapped[User] = relationship(back_populates="categories")
