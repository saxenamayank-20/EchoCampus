from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.cache import get_cache
from backend.app.core.config import settings
from backend.app.core.enums import Role
from backend.app.db.base import now
from backend.app.models import ClosureConfirmation, Complaint, ComplaintHistory
from backend.app.models.confirmation import AUTO_CONFIRMED, PENDING
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.complaint_service import STATS_KEY
from backend.app.services.email_service import EmailSender
from backend.app.services.notification_service import NotificationService


class ConfirmationService:
    """the timed part of the confirmation loop, run by the 15 minute job"""

    def __init__(self, db: Session, sender: EmailSender | None = None):
        self.db = db
        self.sender = sender or EmailSender()
        self.notes = NotificationService(db)

    def _pending(self) -> list[tuple[ClosureConfirmation, Complaint]]:
        rows = self.db.execute(select(ClosureConfirmation, Complaint)
                               .join(Complaint, Complaint.id == ClosureConfirmation.complaint_id)
                               .where(ClosureConfirmation.student_response == PENDING))
        return [tuple(row) for row in rows]

    def send_reminders(self, at: datetime | None = None) -> int:
        """one day before the deadline, remind the student once"""
        at = at or now()
        sent = 0
        for c, ticket in self._pending():
            if not c.reminder_sent and c.due_at - timedelta(days=1) <= at < c.due_at:
                c.reminder_sent = True
                message = f"Reminder: is {ticket.ticket_id} fixed? It will be auto-confirmed on {c.due_at:%d %b %H:%M}."
                self.notes.notify(ticket.student, "confirm_reminder", message, ticket)
                # the link only opens the portal, the student still has to log in to answer
                self.sender.send(ticket.student.email, f"EchoCampus: please confirm {ticket.ticket_id}",
                                 f"{message}\n\nLog in to answer: {settings.frontend_origin}/tickets/{ticket.ticket_id}")
                sent += 1
        self.db.commit()
        return sent

    def auto_confirm_due(self, at: datetime | None = None) -> list[str]:
        """no answer by the deadline -> auto_confirmed, so tickets never get stuck"""
        at = at or now()
        done = []
        admins = UserRepository(self.db).list_users(Role.ADMIN)
        for c, ticket in self._pending():
            if c.due_at <= at:
                c.student_response = AUTO_CONFIRMED
                c.responded_at = at
                self.db.add(ComplaintHistory(complaint=ticket, user=None, action="Auto Confirmed",
                                             note=f"Student didn't answer within {settings.confirmation_window_days} days"))
                self.notes.notify_many(admins, "auto_confirmed",
                                       f"{ticket.ticket_id} was auto-confirmed (no answer from the student).", ticket)
                done.append(ticket.ticket_id)
        self.db.commit()
        if done:
            get_cache().delete(STATS_KEY)
        return done
