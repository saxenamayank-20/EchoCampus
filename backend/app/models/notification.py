from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, now
from backend.app.models.complaint import Complaint
from backend.app.models.user import User


class Notification(Base):
    """in-portal message for one user, shown under the bell icon"""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"))
    type: Mapped[str] = mapped_column(String(30))       # sla_escalated, close_requested, ...
    message: Mapped[str] = mapped_column(String(300))
    is_read: Mapped[bool] = mapped_column(default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(default=now)

    user: Mapped[User] = relationship()
    complaint: Mapped[Complaint | None] = relationship()
