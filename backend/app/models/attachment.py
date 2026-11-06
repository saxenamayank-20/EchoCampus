from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, now
from backend.app.models.complaint import Complaint
from backend.app.models.user import User


class Attachment(Base):
    """proof file on a complaint. the file itself lives in storage under stored_name"""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))   # only for showing, never used as a path
    stored_name: Mapped[str] = mapped_column(String(64), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)

    complaint: Mapped[Complaint] = relationship()
    uploader: Mapped[User] = relationship()


class StoredFile(Base):
    """the bytes of an uploaded file (proof or policy pdf), kept in postgres.
    render's free disk is wiped on every restart, the database isn't"""

    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)   # same as stored_name on the attachment / policy
    data: Mapped[bytes] = mapped_column(LargeBinary)
    size_bytes: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now)
