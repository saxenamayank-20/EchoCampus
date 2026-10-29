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
            created_at=c.created_at, updated_at=c.updated_at, resolved_at=c.resolved_at)


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


class PriorityPreviewOut(BaseModel):
    priority: Priority
