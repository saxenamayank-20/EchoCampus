from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.config import settings
from backend.app.db.base import Base, now
from backend.app.models.user import User


class PolicyDocument(Base):
    """a college policy pdf the admin uploaded. its text lives in policy_chunks"""

    __tablename__ = "policy_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))       # original name, for showing only
    stored_name: Mapped[str] = mapped_column(String(64))     # random name in storage
    pages: Mapped[int]
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)

    uploader: Mapped[User] = relationship()
    chunks: Mapped[list["PolicyChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="PolicyChunk.chunk_index")


class PolicyChunk(Base):
    """one piece (~450 words) of one page, with its embedding for search"""

    __tablename__ = "policy_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("policy_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int]
    page: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(settings.embedding_dim), nullable=True)

    document: Mapped[PolicyDocument] = relationship(back_populates="chunks")
