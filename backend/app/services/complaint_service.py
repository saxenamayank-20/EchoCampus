import json
import random
import string
from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.cache import get_cache
from backend.app.core.config import settings
from backend.app.core.constants import CATEGORIES, MANAGER_MEET_LINKS
from backend.app.core.rate_limit import hit
from backend.app.core.enums import Priority, Role, Status
from backend.app.db.base import now
from backend.app.models import ClosureConfirmation, Complaint, ComplaintHistory, ManagerUpdate, User
from backend.app.models.confirmation import (AUTO_CONFIRMED, CONFIRMED, DISPUTED, PENDING,
                                             WITHDRAWN)
from backend.app.repositories.complaint_repository import ComplaintFilters, ComplaintRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.errors import (ConflictError, DomainError, InvalidInputError,
                                         InvalidTransitionError, NotFoundError, PermissionDeniedError)
from backend.app.services.notification_service import NotificationService
from backend.app.services.priority import KeywordPriorityDetector
from backend.app.services.status_machine import SYSTEM, StatusMachine


STATS_KEY = "admin:stats"
STATS_TTL = 60   # seconds


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
        self.notes = NotificationService(db)

    # ── student side ──────────────────────────────────────────────────────────
    def submit(self, student: User, title: str, description: str, category: str,
               remarks: str = "") -> Complaint:
        title, description = title.strip(), description.strip()
        if not title or not description:
            raise InvalidInputError("Title and description are required.")
        if category not in CATEGORIES:
            raise InvalidInputError(f"Unknown category: {category}")
        # stops spam: 5 complaints per student per hour by default
        hit(f"submit:{student.id}", settings.rate_limit_complaints_per_hour, 3600)

        priority = self.detector.detect(title, description, category)
        filed = now()   # one moment for both, so the sla is exactly N hours after filing
        complaint = Complaint(ticket_id=self._new_ticket_id(), student=student, title=title,
                              description=description, category=category, priority=priority,
                              status=Status.PENDING, student_remarks=remarks.strip() or None,
                              created_at=filed, updated_at=filed,
                              sla_due_at=filed + timedelta(hours=settings.sla_hours(priority)))
        self.complaints.add(complaint)
        self._log(complaint, student, "Complaint Submitted", None, Status.PENDING,
                  f"Priority auto-detected: {priority}")

        # if that manager isn't seeded yet, it just stays pending
        manager = self.users.manager_for_category(category)
        if manager:
            self._assign(complaint, manager)

        self._commit()
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
                last = complaint.latest_confirmation
                if last and last.student_response == PENDING:
                    last.student_response = WITHDRAWN
            complaint.manager_remarks = remark
            self._change_status(complaint, new_status, manager, "Status Updated", remark)

        self._commit()
        return complaint

    def request_close(self, ticket_id: str, manager: User, note: str = "") -> Complaint:
        """manager says it's fixed. the student must confirm before the admin can close"""
        complaint = self._get(ticket_id)
        self._check_assigned_manager(complaint, manager)
        if complaint.status != Status.RESOLVED:
            raise InvalidTransitionError("Only resolved complaints can be sent to the admin for closing.")
        note = note.strip()
        if not note:
            # also covers "after a dispute the manager must add a new note"
            raise InvalidInputError("Add a short note on what was done.")
        last = complaint.latest_confirmation
        if last and last.student_response in (PENDING, CONFIRMED, AUTO_CONFIRMED) and complaint.close_requested:
            raise ConflictError("A close request is already open for this complaint.")

        days = settings.confirmation_window_days
        self.db.add(ClosureConfirmation(complaint=complaint, manager=manager, manager_note=note,
                                        due_at=now() + timedelta(days=days)))
        complaint.close_requested = True
        self._log(complaint, manager, "Close Requested", None, None, note)
        self.notes.notify(complaint.student, "confirm_fix",
                          f"{complaint.ticket_id} was marked resolved. Was it really fixed? "
                          f"Please answer within {days} days.", complaint)
        self._commit()
        return complaint

    # ── student confirms or disputes ─────────────────────────────────────────
    def student_respond(self, ticket_id: str, student: User, fixed: bool,
                        rating: int | None = None, reason: str = "") -> Complaint:
        complaint = self._get(ticket_id)
        if complaint.student_id != student.id:
            raise PermissionDeniedError("Only the student who raised this complaint can answer.")
        confirmation = complaint.latest_confirmation
        if not confirmation or confirmation.student_response != PENDING:
            raise ConflictError("There's nothing to confirm on this complaint right now.")
        confirmation.responded_at = now()
        admins = self.users.list_users(Role.ADMIN)

        if fixed:
            if rating is not None and not 1 <= rating <= 5:
                raise InvalidInputError("Rating must be 1 to 5.")
            confirmation.student_response = CONFIRMED
            confirmation.rating = rating
            self._log(complaint, student, "Student Confirmed", None, None,
                      f"Rating: {rating}/5" if rating else "Student confirmed the fix")
            self.notes.notify_many(admins, "student_confirmed",
                                   f"{complaint.ticket_id}: student confirmed the fix, ready to close.", complaint)
        else:
            reason = reason.strip()
            if not reason:
                raise InvalidInputError("Tell us what's still wrong.")
            confirmation.student_response = DISPUTED
            confirmation.student_reason = reason
            # back to in progress automatically, the close request is cancelled
            self.machine.check(complaint.status, Status.IN_PROGRESS, SYSTEM)
            complaint.close_requested = False
            complaint.resolved_at = None
            self._change_status(complaint, Status.IN_PROGRESS, student, "Student Disputed", reason)
            message = f"{complaint.ticket_id}: student says it's NOT fixed: {reason}"
            self.notes.notify_many(admins, "student_disputed", message, complaint)
            if complaint.manager:
                self.notes.notify(complaint.manager, "student_disputed", message, complaint)
        self._commit()
        return complaint

    def add_manager_update(self, ticket_id: str, manager: User, text: str) -> None:
        complaint = self._get(ticket_id)
        self._check_assigned_manager(complaint, manager)
        if not text.strip():
            raise InvalidInputError("Update message can't be empty.")
        self.complaints.add_manager_update(
            ManagerUpdate(complaint=complaint, manager=manager, update_text=text.strip()))
        self._commit()

    # ── admin side ────────────────────────────────────────────────────────────
    def admin_close(self, ticket_id: str, admin: User, force: bool = False, reason: str = "") -> Complaint:
        """closes a resolved complaint once the student confirmed (or it auto-confirmed).
        force = close anyway, needs a written reason that goes into the history"""
        if admin.role != Role.ADMIN:
            raise PermissionDeniedError("Only the admin can close complaints.")
        complaint = self._get(ticket_id)
        self.machine.check(complaint.status, Status.CLOSED, Role.ADMIN)
        confirmation = complaint.latest_confirmation
        waiting = complaint.close_requested and confirmation and confirmation.student_response == PENDING
        reason = reason.strip()

        if complaint.close_requested and not waiting:
            action, note, decision = "Admin Closed", "Complaint officially closed by Admin", "approved"
        elif not force:
            if waiting:
                raise DomainError(f"Waiting for the student to confirm (until {confirmation.due_at:%d %b %H:%M}). "
                                  "Use override with a reason to close anyway.")
            raise DomainError("The manager hasn't asked to close this complaint yet.")
        elif not reason:
            raise InvalidInputError("A written reason is needed to close without the normal steps.")
        elif waiting:
            action, note, decision = "Admin Override Close", reason, "override"
        else:
            action, note, decision = "Admin Force Closed", reason, "override"

        if confirmation and complaint.close_requested:
            confirmation.admin_decision = decision
            confirmation.admin_note = reason or None
        complaint.close_requested = False
        complaint.resolved_at = now()
        self._change_status(complaint, Status.CLOSED, admin, action, note)
        self.notes.notify(complaint.student, "closed", f"{complaint.ticket_id} was closed by the admin.", complaint)
        self._commit()
        return complaint

    def admin_message(self, ticket_id: str, admin: User, text: str) -> None:
        """admin writes to the manager in the ticket thread (e.g. after a dispute)"""
        complaint = self._get(ticket_id)
        if not text.strip():
            raise InvalidInputError("Message can't be empty.")
        self._log(complaint, admin, "Admin Message", None, None, text.strip())
        if complaint.manager:
            self.notes.notify(complaint.manager, "admin_message",
                              f"Admin on {complaint.ticket_id}: {text.strip()}", complaint)
        self._commit()

    def quality_metrics(self) -> dict:
        """how well managers fix things, judged by the students"""
        rounds = list(self.db.scalars(select(ClosureConfirmation)))
        per_manager: dict[str, dict] = {}
        per_category: dict[str, list[int]] = defaultdict(list)
        for r in rounds:
            m = per_manager.setdefault(r.manager.user_id, {"manager_id": r.manager.user_id, "name": r.manager.name,
                                                           "close_requests": 0, "disputed": 0, "ratings": []})
            m["close_requests"] += 1
            m["disputed"] += r.student_response == DISPUTED
            if r.rating:
                m["ratings"].append(r.rating)
                per_category[self.db.get(Complaint, r.complaint_id).category].append(r.rating)

        managers = []
        for m in per_manager.values():
            ratings = m.pop("ratings")
            m["dispute_rate"] = round(m["disputed"] / m["close_requests"], 2)
            m["avg_rating"] = round(sum(ratings) / len(ratings), 2) if ratings else None
            managers.append(m)
        return {
            "managers": sorted(managers, key=lambda m: m["manager_id"]),
            "categories": {cat: round(sum(v) / len(v), 2) for cat, v in sorted(per_category.items())},
            "reopened_after_close_request": sum(r.student_response == DISPUTED for r in rounds),
        }

    # ── reading ───────────────────────────────────────────────────────────────
    def get_for(self, viewer: User, ticket_id: str) -> Complaint:
        """students see their own, managers the ones assigned to them, admin sees all"""
        complaint = self._get(ticket_id)
        if self._can_view(viewer, complaint):
            return complaint
        raise PermissionDeniedError("You can't view this complaint.")

    def search(self, viewer: User, filters: ComplaintFilters, page: int = 1,
               page_size: int = 20) -> tuple[list[Complaint], int]:
        # the role decides the scope, whatever filters were sent
        if viewer.role == Role.STUDENT:
            filters.student_pk = viewer.id
        elif viewer.role == Role.MANAGER:
            filters.assigned_to = viewer.id
        return self.complaints.search(filters, page, page_size)

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
        stats["Overdue"] = self.complaints.count_escalated_open()
        return stats

    def dashboard(self) -> dict:
        """cards + charts for the admin overview, cached for 60 seconds"""
        cache = get_cache()
        cached = cache.get(STATS_KEY)
        if cached:
            return json.loads(cached)
        data = {"counts": self.stats(), **self.chart_stats()}
        cache.set(STATS_KEY, json.dumps(data), STATS_TTL)
        return data

    def chart_stats(self, days: int = 30) -> dict:
        """numbers for the admin charts"""
        since = (now() - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        per_day = Counter(created.date().isoformat() for created in self.complaints.created_since(since))
        trend = [{"date": (since + timedelta(days=i)).date().isoformat(),
                  "count": per_day.get((since + timedelta(days=i)).date().isoformat(), 0)}
                 for i in range(days)]
        return {
            "by_status": self.complaints.count_by(Complaint.status),
            "by_category": self.complaints.count_by(Complaint.category),
            "by_priority": self.complaints.count_by(Complaint.priority),
            "trend": trend,
        }

    # ── helpers ───────────────────────────────────────────────────────────────
    def _commit(self) -> None:
        """save, then forget the cached admin numbers so the next request recounts"""
        self.db.commit()
        get_cache().delete(STATS_KEY)

    @staticmethod
    def _can_view(viewer: User, complaint: Complaint) -> bool:
        if viewer.role == Role.ADMIN:
            return True
        if viewer.role == Role.STUDENT:
            return complaint.student_id == viewer.id
        return viewer.role == Role.MANAGER and complaint.assigned_to == viewer.id

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
