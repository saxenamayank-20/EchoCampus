from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.enums import Priority, Status
from backend.app.models import Complaint, ComplaintHistory, ManagerUpdate

DONE = (Status.RESOLVED, Status.CLOSED)


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
