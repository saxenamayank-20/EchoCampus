"""Finds open complaints that say the same thing, using embeddings (meaning, not exact words)."""
from sqlalchemy.orm import Session

from backend.app.ai.embeddings import complaint_text
from backend.app.ai.llm_client import LLMClient, LLMError
from backend.app.core.config import settings
from backend.app.core.constants import SENSITIVE_CATEGORIES
from backend.app.core.enums import Status
from backend.app.models import Complaint
from backend.app.repositories.vector_search import nearest

OPEN = (Status.PENDING, Status.ASSIGNED, Status.IN_PROGRESS)


def embed_complaint(llm: LLMClient, title: str, description: str) -> list[float] | None:
    """None when the ai is down: duplicates are a nice extra, never a blocker"""
    try:
        return llm.embed("embedding", [complaint_text(title, description)])[0]
    except LLMError:
        return None


def find_duplicates(db: Session, vector: list[float] | None, exclude_student_id: int | None = None,
                    limit: int = 3) -> list[tuple[Complaint, float]]:
    """open, not merged complaints above DUPLICATE_THRESHOLD, most similar first"""
    if vector is None:
        return []
    conditions = [Complaint.status.in_(OPEN), Complaint.duplicate_of.is_(None),
                  Complaint.category.notin_(SENSITIVE_CATEGORIES)]   # private ones are never suggested
    if exclude_student_id is not None:
        conditions.append(Complaint.student_id != exclude_student_id)
    matches = nearest(db, Complaint, vector, conditions, limit=limit)
    return [(c, score) for c, score in matches if score >= settings.duplicate_threshold]
