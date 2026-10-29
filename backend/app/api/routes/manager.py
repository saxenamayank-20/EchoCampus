from fastapi import APIRouter, BackgroundTasks, status

from backend.app.core.deps import DB, Manager, Sender
from backend.app.core.enums import Role, Status
from backend.app.schemas.complaint import ComplaintOut, ManagerUpdateIn, StatusUpdateIn
from backend.app.schemas.user import MessageOut
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.email_service import status_change_mail

router = APIRouter(prefix="/manager/complaints", tags=["manager"])


@router.get("/{ticket_id}/status-options", response_model=list[Status])
def status_options(ticket_id: str, db: DB, manager: Manager):
    """current status first, then the moves the status machine allows"""
    service = ComplaintService(db)
    complaint = service.get_for(manager, ticket_id)
    return [complaint.status, *service.next_statuses(complaint, Role.MANAGER)]


@router.post("/{ticket_id}/status", response_model=ComplaintOut)
def update_status(ticket_id: str, body: StatusUpdateIn, db: DB, manager: Manager,
                  sender: Sender, background: BackgroundTasks):
    complaint = ComplaintService(db).update_status(ticket_id, body.status, manager, body.remark)
    # the mail goes out after the response, so the manager doesn't wait for smtp
    background.add_task(status_change_mail, sender, complaint.student.email,
                        complaint.ticket_id, complaint.status.value, complaint.manager_remarks)
    return ComplaintOut.of(complaint)


@router.post("/{ticket_id}/close-request", response_model=ComplaintOut)
def request_close(ticket_id: str, db: DB, manager: Manager):
    return ComplaintOut.of(ComplaintService(db).request_close(ticket_id, manager))


@router.post("/{ticket_id}/updates", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def post_update(ticket_id: str, body: ManagerUpdateIn, db: DB, manager: Manager):
    ComplaintService(db).add_manager_update(ticket_id, manager, body.text)
    return MessageOut(message="Update sent to the admin.")
