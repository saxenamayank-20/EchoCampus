from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.enums import Priority, Status
from backend.app.db.base import Base, enum_column, now
from backend.app.models.user import User


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaints_assigned_status", "assigned_to", "status"),
        Index("ix_complaints_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(20), unique=True)   # TKT-ABC12345
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))
    priority: Mapped[Priority] = mapped_column(enum_column(Priority))
    priority_source: Mapped[str] = mapped_column(String(10), default="keyword")  # keyword / ai / manual
    status: Mapped[Status] = mapped_column(enum_column(Status), default=Status.PENDING)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    student_remarks: Mapped[str | None] = mapped_column(Text)
    manager_remarks: Mapped[str | None] = mapped_column(Text)
    meet_link: Mapped[str | None] = mapped_column(String(255))
    close_requested: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)
    resolved_at: Mapped[datetime | None]

    # names and emails come from these joins, not copied into this table
    student: Mapped[User] = relationship(foreign_keys=[student_id])
    manager: Mapped[User | None] = relationship(foreign_keys=[assigned_to])
    history: Mapped[list["ComplaintHistory"]] = relationship(
        back_populates="complaint", order_by="ComplaintHistory.id")

    def __repr__(self) -> str:
        return f"<Complaint {self.ticket_id} {self.status}>"


class ComplaintHistory(Base):
    __tablename__ = "complaint_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # empty = done by the system
    action: Mapped[str] = mapped_column(String(50))
    old_status: Mapped[Status | None] = mapped_column(enum_column(Status))
    new_status: Mapped[Status | None] = mapped_column(enum_column(Status))
    note: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(default=now)

    complaint: Mapped[Complaint] = relationship(back_populates="history")
    user: Mapped[User | None] = relationship()


class ManagerUpdate(Base):
    """progress notes a manager sends to the admin"""

    __tablename__ = "manager_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"))
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    update_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now)

    complaint: Mapped[Complaint] = relationship()
    manager: Mapped[User] = relationship()
