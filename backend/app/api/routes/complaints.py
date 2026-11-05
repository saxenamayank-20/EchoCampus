from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from backend.app.core.deps import DB, LLM, CurrentUser, Student
from backend.app.core.enums import Priority, Status
from backend.app.repositories.complaint_repository import ComplaintFilters
from backend.app.schemas.complaint import (
    ComplaintIn,
    ComplaintOut,
    ConfirmIn,
    DuplicateOut,
    HistoryOut,
    Page,
    PreviewIn,
    PreviewOut,
    PriorityPreviewOut,
    TextIn,
)
from backend.app.schemas.user import MessageOut
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.priority import KeywordPriorityDetector

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def submit(body: ComplaintIn, db: DB, student: Student, llm: LLM):
    complaint = ComplaintService(db, llm=llm).submit(student, body.title, body.description, body.category, body.remarks)
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
    close_requested: bool | None = None,
    escalated: bool | None = None,
):
    """students get their own, managers their assigned ones, admin gets everything"""
    filters = ComplaintFilters(statuses=status_, category=category, priority=priority,
                               date_from=date_from, date_to=date_to, search=q,
                               close_requested=close_requested, escalated=escalated)
    items, total = ComplaintService(db).search(user, filters, page, page_size)
    return Page(items=[ComplaintOut.of(c) for c in items], total=total, page=page, page_size=page_size)


@router.post("/preview", response_model=PreviewOut)
def preview(body: PreviewIn, db: DB, student: Student, llm: LLM):
    """before submit: ai category + priority, crisis help, and similar open complaints"""
    result = ComplaintService(db, llm=llm).preview(student, body.title, body.description, body.category)
    t = result["triage"]
    return PreviewOut(
        suggested_category=t.category_suggested, priority=t.priority, priority_source=t.priority_source,
        summary=t.summary, used_ai=t.used_ai, crisis=result["crisis"],
        duplicates=[DuplicateOut(ticket_id=c.ticket_id, title=c.title, category=c.category, status=c.status,
                                 supporters_count=len(c.supporters), similarity=round(score, 3))
                    for c, score in result["duplicates"]])


@router.get("/supporting", response_model=list[ComplaintOut])
def supporting(db: DB, student: Student):
    """complaints this student said "I have this issue too" on"""
    return [ComplaintOut.of(c) for c in ComplaintService(db).supported_by(student)]


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


@router.post("/{ticket_id}/confirm", response_model=ComplaintOut)
def confirm(ticket_id: str, body: ConfirmIn, db: DB, student: Student):
    """student answers: fixed (with an optional 1-5 rating) or not fixed (reason needed)"""
    return ComplaintOut.of(ComplaintService(db).student_respond(
        ticket_id, student, body.fixed, body.rating, body.reason))


@router.post("/{ticket_id}/support", response_model=ComplaintOut)
def support(ticket_id: str, db: DB, student: Student):
    return ComplaintOut.of(ComplaintService(db).support(ticket_id, student))


@router.post("/{ticket_id}/supporter-comment", response_model=MessageOut)
def supporter_comment(ticket_id: str, body: TextIn, db: DB, student: Student):
    ComplaintService(db).supporter_comment(ticket_id, student, body.text)
    return MessageOut(message="Thanks, the admin can see your comment.")
