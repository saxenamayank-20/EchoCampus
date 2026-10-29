import random
import string
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.app.core.constants import CATEGORIES, MANAGER_MEET_LINKS
from backend.app.core.enums import Priority, Role, Status
from backend.app.db.base import now
from backend.app.models import Complaint, ComplaintHistory, ManagerUpdate, User
from backend.app.repositories.complaint_repository import ComplaintRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.errors import (DomainError, InvalidInputError, InvalidTransitionError,
                                         NotFoundError, PermissionDeniedError)
from backend.app.services.priority import KeywordPriorityDetector
from backend.app.services.status_machine import SYSTEM, StatusMachine


def generate_ticket_id() -> str:
    """TKT- + 3 capital letters + 5 digits, e.g. TKT-ABC12345"""
    letters = "".join(random.choices(string.ascii_uppercase, k=3))
    digits = "".join(random.choices(string.digits, k=5))
    return f"TKT-{letters}{digits}"


class ComplaintService:
    """all the complaint rules: routing, priority, status changes, history"""

    def __init__(self, db: Session, detector: KeywordPriorityDetector | None = None,
                 machine: StatusMachine | None = None):
        self.db = db
        self.users = UserRepository(db)
        self.complaints = ComplaintRepository(db)
        self.detector = detector or KeywordPriorityDetector()
        self.machine = machine or StatusMachine()

    # ── student side ──────────────────────────────────────────────────────────
    def submit(self, student: User, title: str, description: str, category: str,
               remarks: str = "") -> Complaint:
        title, description = title.strip(), description.strip()
        if not title or not description:
            raise InvalidInputError("Title and description are required.")
        if category not in CATEGORIES:
            raise InvalidInputError(f"Unknown category: {category}")

        priority = self.detector.detect(title, description, category)
        complaint = Complaint(ticket_id=self._new_ticket_id(), student=student, title=title,
                              description=description, category=category, priority=priority,
                              status=Status.PENDING, student_remarks=remarks.strip() or None)
        self.complaints.add(complaint)
        self._log(complaint, student, "Complaint Submitted", None, Status.PENDING,
                  f"Priority auto-detected: {priority}")

        # if that manager isn't seeded yet, it just stays pending
        manager = self.users.manager_for_category(category)
        if manager:
            self._assign(complaint, manager)

        self.db.commit()
        return complaint

    # ── manager side ──────────────────────────────────────────────────────────
    def update_status(self, ticket_id: str, new_status: str, manager: User,
                      remark: str = "") -> Complaint:
        complaint = self._get(ticket_id)
        self._check_assigned_manager(complaint, manager)
        new_status = self._to_status(new_status)
        remark = remark.strip() or None

        if new_status == complaint.status:
            # same status, the manager only changed the remark
            complaint.manager_remarks = remark
            self._log(complaint, manager, "Remark Updated", None, None, remark)
        else:
            self.machine.check(complaint.status, new_status, Role.MANAGER)
            if new_status == Status.RESOLVED:
                complaint.resolved_at = now()
            elif complaint.status == Status.RESOLVED:
                # reopened, so the old close request doesn't count anymore
                complaint.resolved_at = None
                complaint.close_requested = False
            complaint.manager_remarks = remark
            self._change_status(complaint, new_status, manager, "Status Updated", remark)

        self.db.commit()
        return complaint

    def request_close(self, ticket_id: str, manager: User) -> Complaint:
        complaint = self._get(ticket_id)
        self._check_assigned_manager(complaint, manager)
        if complaint.status != Status.RESOLVED:
            raise InvalidTransitionError("Only resolved complaints can be sent to the admin for closing.")
        if not complaint.close_requested:
            complaint.close_requested = True
            self._log(complaint, manager, "Close Requested", None, None,
                      "Manager sent close request to Admin")
            self.db.commit()
        return complaint

    def add_manager_update(self, ticket_id: str, manager: User, text: str) -> None:
        complaint = self._get(ticket_id)
        self._check_assigned_manager(complaint, manager)
        if not text.strip():
            raise InvalidInputError("Update message can't be empty.")
        self.complaints.add_manager_update(
            ManagerUpdate(complaint=complaint, manager=manager, update_text=text.strip()))
        self.db.commit()

    # ── admin side ────────────────────────────────────────────────────────────
    def admin_close(self, ticket_id: str, admin: User, force: bool = False) -> Complaint:
        """closes a resolved complaint. force skips the manager's close request (logged in history)"""
        if admin.role != Role.ADMIN:
            raise PermissionDeniedError("Only the admin can close complaints.")
        complaint = self._get(ticket_id)
        if not complaint.close_requested and not force:
            raise DomainError("The manager hasn't asked to close this complaint yet.")
        self.machine.check(complaint.status, Status.CLOSED, Role.ADMIN)

        complaint.close_requested = False
        complaint.resolved_at = now()
        if force:
            self._change_status(complaint, Status.CLOSED, admin, "Admin Force Closed",
                                "Closed by Admin without a close request")
        else:
            self._change_status(complaint, Status.CLOSED, admin, "Admin Closed",
                                "Complaint officially closed by Admin")
        self.db.commit()
        return complaint

    # ── reading ───────────────────────────────────────────────────────────────
    def get(self, ticket_id: str) -> Complaint:
        return self._get(ticket_id)

    def for_student(self, student: User) -> list[Complaint]:
        return self.complaints.list_for_student(student.id)

    def for_manager(self, manager: User, resolved: bool = False) -> list[Complaint]:
        return self.complaints.list_for_manager(manager.id, resolved)

    def all(self) -> list[Complaint]:
        return self.complaints.list_all()

    def open_by_category(self) -> dict[str, list[Complaint]]:
        grouped = defaultdict(list)
        for complaint in self.complaints.list_not_closed():
            grouped[complaint.category].append(complaint)
        return dict(grouped)

    def resolved_or_close_requested(self) -> list[Complaint]:
        return self.complaints.list_resolved_or_close_requested()

    def timeline(self, ticket_id: str) -> list[ComplaintHistory]:
        return self._get(ticket_id).history

    def manager_updates(self) -> list[ManagerUpdate]:
        return self.complaints.list_manager_updates()

    def next_statuses(self, complaint: Complaint, actor: str) -> list[Status]:
        return self.machine.next_statuses(complaint.status, actor)

    def stats(self) -> dict[str, int]:
        stats = {status.value: self.complaints.count(status) for status in Status}
        stats["Total"] = self.complaints.count()
        stats["Students"] = self.users.count(Role.STUDENT)
        stats["PendingClose"] = self.complaints.count_close_requested()
        stats["OpenCritical"] = self.complaints.count_open_critical()
        return stats

    # ── helpers ───────────────────────────────────────────────────────────────
    def _get(self, ticket_id: str) -> Complaint:
        complaint = self.complaints.get_by_ticket(ticket_id)
        if not complaint:
            raise NotFoundError(f"Ticket {ticket_id} not found.")
        return complaint

    def _new_ticket_id(self) -> str:
        ticket_id = generate_ticket_id()
        while self.complaints.ticket_exists(ticket_id):
            ticket_id = generate_ticket_id()
        return ticket_id

    @staticmethod
    def _to_status(value: str) -> Status:
        try:
            return Status(value)
        except ValueError:
            raise InvalidInputError(f"Unknown status: {value}") from None

    @staticmethod
    def _check_assigned_manager(complaint: Complaint, manager: User) -> None:
        if manager.role != Role.MANAGER or complaint.assigned_to != manager.id:
            raise PermissionDeniedError("This complaint isn't assigned to you.")

    def _assign(self, complaint: Complaint, manager: User) -> None:
        self.machine.check(complaint.status, Status.ASSIGNED, SYSTEM)
        complaint.manager = manager
        note = f"Assigned to {manager.name}"
        if complaint.priority == Priority.CRITICAL:
            complaint.meet_link = MANAGER_MEET_LINKS.get(manager.user_id)
            note += " | CRITICAL: Google Meet link generated"
        self._change_status(complaint, Status.ASSIGNED, None, "Assigned", note)

    def _change_status(self, complaint: Complaint, new: Status, by: User | None,
                       action: str, note: str | None) -> None:
        """every status change goes through here, so history is never skipped"""
        old = complaint.status
        complaint.status = new
        self._log(complaint, by, action, old, new, note)

    def _log(self, complaint: Complaint, by: User | None, action: str,
             old: Status | None, new: Status | None, note: str | None) -> None:
        self.complaints.add_history(ComplaintHistory(
            complaint=complaint, user=by, action=action,
            old_status=old, new_status=new, note=note))
