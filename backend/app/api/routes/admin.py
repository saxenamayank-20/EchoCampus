from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query

from backend.app.core.deps import DB, Admin, Sender
from backend.app.core.enums import Role
from backend.app.schemas.complaint import (AdminCloseIn, AdminMessageIn, ComplaintOut, ManagerUpdateOut,
                                           MergeIn, Page)
from backend.app.schemas.user import MessageOut, UserOut
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.email_service import status_change_mail
from backend.app.services.sla_service import SlaService
from backend.app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["admin"])

PageNo = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("/stats")
def stats(db: DB, _: Admin):
    """card numbers + chart data for the overview (cached 60 s)"""
    return ComplaintService(db).dashboard()


@router.post("/sla/run")
def run_sla_check(db: DB, _: Admin, sender: Sender):
    """same job the scheduler runs every 15 minutes, on demand"""
    escalated = SlaService(db, sender).escalate_overdue()
    return {"escalated": [c.ticket_id for c in escalated]}


@router.get("/users", response_model=Page[UserOut])
def users(db: DB, _: Admin, role: Role | None = None, page: PageNo = 1, page_size: PageSize = 20):
    everyone = UserService(db).list_users(role)
    start = (page - 1) * page_size
    return Page(items=[UserOut.of(u) for u in everyone[start:start + page_size]],
                total=len(everyone), page=page, page_size=page_size)


@router.get("/manager-updates", response_model=Page[ManagerUpdateOut])
def manager_updates(db: DB, _: Admin, page: PageNo = 1, page_size: PageSize = 20):
    updates = ComplaintService(db).manager_updates()
    start = (page - 1) * page_size
    return Page(items=[ManagerUpdateOut.of(m) for m in updates[start:start + page_size]],
                total=len(updates), page=page, page_size=page_size)


@router.post("/complaints/{ticket_id}/close", response_model=ComplaintOut)
def close(ticket_id: str, body: AdminCloseIn, db: DB, admin: Admin,
          sender: Sender, background: BackgroundTasks):
    complaint = ComplaintService(db).admin_close(ticket_id, admin, force=body.force, reason=body.reason)
    background.add_task(status_change_mail, sender, complaint.student.email,
                        complaint.ticket_id, complaint.status.value, None)
    return ComplaintOut.of(complaint)


@router.post("/complaints/{ticket_id}/message", response_model=MessageOut)
def message_manager(ticket_id: str, body: AdminMessageIn, db: DB, admin: Admin):
    ComplaintService(db).admin_message(ticket_id, admin, body.text)
    return MessageOut(message="Message sent to the manager.")


@router.get("/quality")
def quality(db: DB, _: Admin):
    """dispute rate and student ratings per manager and category"""
    return ComplaintService(db).quality_metrics()


@router.post("/complaints/{ticket_id}/merge", response_model=ComplaintOut)
def merge(ticket_id: str, body: MergeIn, db: DB, admin: Admin):
    """ticket_id is a duplicate: close it and add its student as a supporter of `into`"""
    return ComplaintOut.of(ComplaintService(db).merge(ticket_id, body.into.strip(), admin))
