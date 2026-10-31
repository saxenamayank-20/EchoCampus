from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, now
from backend.app.models.user import User

# student_response values
PENDING, CONFIRMED, DISPUTED, AUTO_CONFIRMED = "pending", "confirmed", "disputed", "auto_confirmed"
WITHDRAWN = "withdrawn"   # the manager reopened it before the student answered


class ClosureConfirmation(Base):
    """one row per close request. the student says fixed or not before the admin closes.
    a ticket can have several rounds (request -> dispute -> fix -> request again)"""

    __tablename__ = "closure_confirmations"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    manager_note: Mapped[str] = mapped_column(Text)
    student_response: Mapped[str] = mapped_column(String(20), default=PENDING)
    student_reason: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None]                                   # 1-5, only when confirmed
    due_at: Mapped[datetime]                                     # after this it auto-confirms
    responded_at: Mapped[datetime | None]
    reminder_sent: Mapped[bool] = mapped_column(default=False, server_default=false())
    admin_decision: Mapped[str | None] = mapped_column(String(20))   # approved / override
    admin_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now)

    manager: Mapped[User] = relationship()
    complaint: Mapped["Complaint"] = relationship(back_populates="confirmations")  # noqa: F821
