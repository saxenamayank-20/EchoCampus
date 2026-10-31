from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.models import Complaint, Notification, User
from backend.app.services.errors import NotFoundError


class NotificationService:
    """the bell icon: small messages for one user"""

    def __init__(self, db: Session):
        self.db = db

    def notify(self, user: User, kind: str, message: str, complaint: Complaint | None = None) -> None:
        # no commit here, it's saved together with the change that caused it
        self.db.add(Notification(user=user, complaint=complaint, type=kind, message=message[:300]))

    def notify_many(self, users: list[User], kind: str, message: str, complaint: Complaint | None = None) -> None:
        for user in users:
            self.notify(user, kind, message, complaint)

    def list_for(self, user: User, limit: int = 30) -> list[Notification]:
        return list(self.db.scalars(select(Notification).where(Notification.user_id == user.id)
                                    .order_by(Notification.id.desc()).limit(limit)))

    def unread_count(self, user: User) -> int:
        return self.db.scalar(select(func.count()).select_from(Notification)
                              .where(Notification.user_id == user.id, Notification.is_read.is_(False)))

    def mark_read(self, user: User, notification_id: int) -> None:
        n = self.db.get(Notification, notification_id)
        if not n or n.user_id != user.id:   # someone else's notification looks the same as a missing one
            raise NotFoundError("Notification not found.")
        n.is_read = True
        self.db.commit()

    def mark_all_read(self, user: User) -> None:
        self.db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
        self.db.commit()
