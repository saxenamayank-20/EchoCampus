from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, now
from backend.app.models.user import User


class LLMCall(Base):
    """one row per call to the ai provider: for cost, speed and failure tracking"""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature: Mapped[str] = mapped_column(String(20))      # triage / embedding / rag / reply / insights
    model: Mapped[str] = mapped_column(String(60))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    latency_ms: Mapped[int]
    success: Mapped[bool]
    error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=now)


class ComplaintSupporter(Base):
    """'I have this issue too': a student backing someone else's complaint"""

    __tablename__ = "complaint_supporters"
    __table_args__ = (UniqueConstraint("complaint_id", "student_id", name="uq_supporter_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)

    student: Mapped[User] = relationship()
    complaint: Mapped["Complaint"] = relationship(back_populates="supporters")  # noqa: F821


class InsightReport(Base):
    """the weekly ai report for the admin. stats = the exact numbers it was written from"""

    __tablename__ = "insight_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    period_start: Mapped[datetime]
    period_end: Mapped[datetime]
    stats: Mapped[str] = mapped_column(Text)              # json
    report: Mapped[str] = mapped_column(Text)
    used_ai: Mapped[bool]                                 # false = the plain template (ai down / failed the check)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))   # none = the weekly job
    created_at: Mapped[datetime] = mapped_column(default=now, index=True)
