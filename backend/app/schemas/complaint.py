from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from backend.app.core.enums import Priority, Status
from backend.app.models import Complaint, ComplaintHistory, ManagerUpdate

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """one page of a list, plus the numbers the ui needs for paging"""
    items: list[T]
    total: int
    page: int
    page_size: int


class ComplaintIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    category: str
    remarks: str = Field(default="", max_length=1000)


class ConfirmationOut(BaseModel):
    response: str                 # pending / confirmed / disputed / auto_confirmed / withdrawn
    manager_note: str
    student_reason: str | None
    rating: int | None
    due_at: datetime
    responded_at: datetime | None
    admin_decision: str | None
    admin_note: str | None


class ComplaintOut(BaseModel):
    ticket_id: str
    title: str
    description: str
    category: str
    priority: Priority
    priority_source: str
    status: Status
    student_id: str
    student_name: str
    student_dept: str | None
    assigned_to: str | None
    manager_name: str | None
    student_remarks: str | None
    manager_remarks: str | None
    meet_link: str | None
    close_requested: bool
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    sla_due_at: datetime | None
    escalated: bool
    confirmation: ConfirmationOut | None    # latest close-request round

    @classmethod
    def of(cls, c: Complaint) -> "ComplaintOut":
        return cls(
            ticket_id=c.ticket_id, title=c.title, description=c.description, category=c.category,
            priority=c.priority, priority_source=c.priority_source, status=c.status,
            student_id=c.student.user_id, student_name=c.student.name, student_dept=c.student.department,
            assigned_to=c.manager.user_id if c.manager else None,
            manager_name=c.manager.name if c.manager else None,
            student_remarks=c.student_remarks, manager_remarks=c.manager_remarks,
            meet_link=c.meet_link, close_requested=c.close_requested,
            created_at=c.created_at, updated_at=c.updated_at, resolved_at=c.resolved_at,
            sla_due_at=c.sla_due_at, escalated=c.escalated, confirmation=_confirmation(c))


def _confirmation(c: Complaint) -> ConfirmationOut | None:
    r = c.latest_confirmation
    if not r:
        return None
    return ConfirmationOut(response=r.student_response, manager_note=r.manager_note,
                           student_reason=r.student_reason, rating=r.rating, due_at=r.due_at,
                           responded_at=r.responded_at, admin_decision=r.admin_decision,
                           admin_note=r.admin_note)


class HistoryOut(BaseModel):
    action: str
    old_status: Status | None
    new_status: Status | None
    note: str | None
    changed_by: str
    timestamp: datetime

    @classmethod
    def of(cls, h: ComplaintHistory) -> "HistoryOut":
        return cls(action=h.action, old_status=h.old_status, new_status=h.new_status, note=h.note,
                   changed_by=h.user.user_id if h.user else "system", timestamp=h.timestamp)


class StatusUpdateIn(BaseModel):
    status: Status
    remark: str = Field(default="", max_length=2000)


class ManagerUpdateIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ManagerUpdateOut(BaseModel):
    ticket_id: str
    title: str
    category: str
    priority: Priority
    status: Status
    manager_id: str
    manager_name: str
    update_text: str
    created_at: datetime

    @classmethod
    def of(cls, m: ManagerUpdate) -> "ManagerUpdateOut":
        c = m.complaint
        return cls(ticket_id=c.ticket_id, title=c.title, category=c.category, priority=c.priority,
                   status=c.status, manager_id=m.manager.user_id, manager_name=m.manager.name,
                   update_text=m.update_text, created_at=m.created_at)


class AdminCloseIn(BaseModel):
    force: bool = False
    reason: str = Field(default="", max_length=2000)


class CloseRequestIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class ConfirmIn(BaseModel):
    fixed: bool
    rating: int | None = Field(default=None, ge=1, le=5)
    reason: str = Field(default="", max_length=2000)


class AdminMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class PriorityPreviewOut(BaseModel):
    priority: Priority
