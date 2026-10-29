from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from backend.app.core.deps import DB, CurrentUser, Student
from backend.app.core.enums import Priority, Status
from backend.app.repositories.complaint_repository import ComplaintFilters
from backend.app.schemas.complaint import (ComplaintIn, ComplaintOut, HistoryOut, Page,
                                           PriorityPreviewOut)
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.priority import KeywordPriorityDetector

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def submit(body: ComplaintIn, db: DB, student: Student):
    complaint = ComplaintService(db).submit(student, body.title, body.description, body.category, body.remarks)
    return ComplaintOut.of(complaint)


@router.get("", response_model=Page[ComplaintOut])
def list_complaints(
    db: DB, user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_: Annotated[list[Status] | None, Query(alias="status")] = None,
    category: str | None = None,
    priority: Priority | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
):
    """students get their own, managers their assigned ones, admin gets everything"""
    filters = ComplaintFilters(statuses=status_, category=category, priority=priority,
                               date_from=date_from, date_to=date_to, search=q)
    items, total = ComplaintService(db).search(user, filters, page, page_size)
    return Page(items=[ComplaintOut.of(c) for c in items], total=total, page=page, page_size=page_size)


@router.get("/priority-preview", response_model=PriorityPreviewOut)
def priority_preview(_: Student, title: str = "", description: str = "", category: str = ""):
    """live hint on the new complaint form"""
    return PriorityPreviewOut(priority=KeywordPriorityDetector().detect(title, description, category))


@router.get("/{ticket_id}", response_model=ComplaintOut)
def get_one(ticket_id: str, db: DB, user: CurrentUser):
    return ComplaintOut.of(ComplaintService(db).get_for(user, ticket_id))


@router.get("/{ticket_id}/timeline", response_model=list[HistoryOut])
def timeline(ticket_id: str, db: DB, user: CurrentUser):
    complaint = ComplaintService(db).get_for(user, ticket_id)
    return [HistoryOut.of(h) for h in complaint.history]
