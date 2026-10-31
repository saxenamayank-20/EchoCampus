from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.core.cache import get_cache
from backend.app.core.enums import Role
from backend.app.db.base import now
from backend.app.models import Complaint, ComplaintHistory
from backend.app.repositories.complaint_repository import ComplaintRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.complaint_service import STATS_KEY
from backend.app.services.email_service import EmailSender
from backend.app.services.notification_service import NotificationService


class SlaService:
    """finds complaints that are still open after their sla time and escalates them"""

    def __init__(self, db: Session, sender: EmailSender | None = None):
        self.db = db
        self.sender = sender or EmailSender()
        self.complaints = ComplaintRepository(db)
        self.users = UserRepository(db)
        self.notes = NotificationService(db)

    def escalate_overdue(self, at: datetime | None = None) -> list[Complaint]:
        """at = 'now' (tests pass a time in the future to fake waiting)"""
        at = at or now()
        overdue = self.complaints.overdue(at)
        if not overdue:
            return []

        admins = self.users.list_users(Role.ADMIN)
        for c in overdue:
            c.escalated = True
            c.escalated_at = at
            # status stays the same, only the flag changes, so no status move is needed
            self.complaints.add_history(ComplaintHistory(
                complaint=c, user=None, action="SLA Escalated",
                note=f"{c.priority} complaint not resolved by {c.sla_due_at:%d %b %H:%M}"))
            message = f"{c.ticket_id} ({c.priority}) is overdue: {c.title}"
            self.notes.notify_many(admins, "sla_escalated", message, c)
            if c.manager:
                self.notes.notify(c.manager, "sla_escalated", message, c)
        self.db.commit()
        get_cache().delete(STATS_KEY)

        lines = "\n".join(f"- {c.ticket_id} ({c.priority}, {c.category}): {c.title}" for c in overdue)
        for admin in admins:
            self.sender.send(admin.email, f"EchoCampus: {len(overdue)} complaint(s) overdue",
                             f"These complaints passed their SLA time:\n\n{lines}")
        return overdue
