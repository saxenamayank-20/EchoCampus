from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.enums import Priority, Status
from backend.app.models import Complaint, ComplaintHistory, ManagerUpdate

DONE = (Status.RESOLVED, Status.CLOSED)


@dataclass
class ComplaintFilters:
    """everything is optional, only the filled ones are used"""
    student_pk: int | None = None
    assigned_to: int | None = None
    statuses: list[Status] | None = None
    category: str | None = None
    priority: Priority | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None    # matches ticket id or title
    close_requested: bool | None = None


class ComplaintRepository:
    """only talks to the db, no business rules here"""

    def __init__(self, db: Session):
        self.db = db

    def add(self, complaint: Complaint) -> Complaint:
        self.db.add(complaint)
        self.db.flush()
        return complaint

    def get_by_ticket(self, ticket_id: str) -> Complaint | None:
        return self.db.scalar(select(Complaint).where(Complaint.ticket_id == ticket_id))

    def ticket_exists(self, ticket_id: str) -> bool:
        return self.get_by_ticket(ticket_id) is not None

    def list_for_student(self, student_pk: int) -> list[Complaint]:
        return list(self.db.scalars(
            select(Complaint).where(Complaint.student_id == student_pk)
            .order_by(Complaint.created_at.desc())))

    def list_for_manager(self, manager_pk: int, resolved: bool) -> list[Complaint]:
        query = select(Complaint).where(Complaint.assigned_to == manager_pk)
        if resolved:
            query = query.where(Complaint.status.in_(DONE)).order_by(Complaint.updated_at.desc())
        else:
            query = query.where(Complaint.status.not_in(DONE)).order_by(Complaint.created_at.desc())
        return list(self.db.scalars(query))

    def list_all(self) -> list[Complaint]:
        return list(self.db.scalars(select(Complaint).order_by(Complaint.created_at.desc())))

    def list_not_closed(self) -> list[Complaint]:
        return list(self.db.scalars(
            select(Complaint).where(Complaint.status != Status.CLOSED)
            .order_by(Complaint.created_at.desc())))

    def list_resolved_or_close_requested(self) -> list[Complaint]:
        return list(self.db.scalars(
            select(Complaint)
            .where(Complaint.status.in_(DONE) | Complaint.close_requested.is_(True))
            .order_by(Complaint.updated_at.desc())))

    def search(self, f: ComplaintFilters, page: int, page_size: int) -> tuple[list[Complaint], int]:
        """one page of complaints + the total count, newest first"""
        conditions = []
        if f.student_pk is not None:
            conditions.append(Complaint.student_id == f.student_pk)
        if f.assigned_to is not None:
            conditions.append(Complaint.assigned_to == f.assigned_to)
        if f.statuses:
            conditions.append(Complaint.status.in_(f.statuses))
        if f.category:
            conditions.append(Complaint.category == f.category)
        if f.priority:
            conditions.append(Complaint.priority == f.priority)
        if f.date_from:
            conditions.append(Complaint.created_at >= datetime.combine(f.date_from, datetime.min.time()))
        if f.date_to:
            # date_to counts the whole day, so stop at the next midnight
            conditions.append(Complaint.created_at < datetime.combine(f.date_to + timedelta(days=1),
                                                                      datetime.min.time()))
        if f.close_requested is not None:
            conditions.append(Complaint.close_requested.is_(f.close_requested))
        if f.search:
            like = f"%{f.search.strip()}%"
            conditions.append(or_(Complaint.ticket_id.ilike(like), Complaint.title.ilike(like)))

        total = self.db.scalar(select(func.count()).select_from(Complaint).where(*conditions))
        items = self.db.scalars(select(Complaint).where(*conditions)
                                .order_by(Complaint.created_at.desc(), Complaint.id.desc())
                                .offset((page - 1) * page_size).limit(page_size))
        return list(items), total

    def count_by(self, column) -> dict[str, int]:
        rows = self.db.execute(select(column, func.count()).group_by(column))
        return {str(key): n for key, n in rows}

    def created_since(self, since: datetime) -> list[datetime]:
        return list(self.db.scalars(select(Complaint.created_at).where(Complaint.created_at >= since)))

    def add_history(self, entry: ComplaintHistory) -> None:
        self.db.add(entry)

    def add_manager_update(self, update: ManagerUpdate) -> None:
        self.db.add(update)

    def list_manager_updates(self) -> list[ManagerUpdate]:
        return list(self.db.scalars(select(ManagerUpdate).order_by(ManagerUpdate.created_at.desc())))

    def count(self, status: Status | None = None) -> int:
        query = select(func.count()).select_from(Complaint)
        if status:
            query = query.where(Complaint.status == status)
        return self.db.scalar(query)

    def count_close_requested(self) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.close_requested.is_(True)))

    def count_open_critical(self) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Complaint)
            .where(Complaint.priority == Priority.CRITICAL, Complaint.status.not_in(DONE)))
