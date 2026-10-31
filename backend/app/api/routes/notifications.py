from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.core.deps import DB, CurrentUser
from backend.app.models import Notification
from backend.app.schemas.user import MessageOut
from backend.app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: int
    type: str
    message: str
    ticket_id: str | None
    is_read: bool
    created_at: datetime

    @classmethod
    def of(cls, n: Notification) -> "NotificationOut":
        return cls(id=n.id, type=n.type, message=n.message, is_read=n.is_read, created_at=n.created_at,
                   ticket_id=n.complaint.ticket_id if n.complaint else None)


class NotificationsOut(BaseModel):
    unread: int
    items: list[NotificationOut]


@router.get("", response_model=NotificationsOut)
def my_notifications(db: DB, user: CurrentUser):
    service = NotificationService(db)
    return NotificationsOut(unread=service.unread_count(user),
                            items=[NotificationOut.of(n) for n in service.list_for(user)])


@router.post("/{notification_id}/read", response_model=MessageOut)
def mark_read(notification_id: int, db: DB, user: CurrentUser):
    NotificationService(db).mark_read(user, notification_id)
    return MessageOut(message="ok")


@router.post("/read-all", response_model=MessageOut)
def mark_all_read(db: DB, user: CurrentUser):
    NotificationService(db).mark_all_read(user)
    return MessageOut(message="ok")
