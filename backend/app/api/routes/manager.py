from fastapi import APIRouter, BackgroundTasks, status

from backend.app.ai.reply_suggest import suggest_reply
from backend.app.core.config import settings
from backend.app.core.deps import DB, LLM, Manager, Sender
from backend.app.core.enums import Role, Status
from backend.app.core.rate_limit import hit
from backend.app.schemas.complaint import CloseRequestIn, ComplaintOut, ManagerUpdateIn, PriorityIn, StatusUpdateIn
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
def request_close(ticket_id: str, body: CloseRequestIn, db: DB, manager: Manager,
                  sender: Sender, background: BackgroundTasks):
    complaint = ComplaintService(db).request_close(ticket_id, manager, body.note)
    # the link only opens the portal, answering still needs a login
    background.add_task(sender.send, complaint.student.email,
                        f"EchoCampus: was {complaint.ticket_id} fixed?",
                        f"Your complaint {complaint.ticket_id} was marked resolved.\n"
                        f"Manager's note: {body.note}\n\nWas it really fixed? Log in to answer within "
                        f"{settings.confirmation_window_days} days: "
                        f"{settings.frontend_origin}/tickets/{complaint.ticket_id}")
    return ComplaintOut.of(complaint)


@router.post("/{ticket_id}/updates", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def post_update(ticket_id: str, body: ManagerUpdateIn, db: DB, manager: Manager):
    ComplaintService(db).add_manager_update(ticket_id, manager, body.text)
    return MessageOut(message="Update sent to the admin.")


@router.post("/{ticket_id}/priority", response_model=ComplaintOut)
def set_priority(ticket_id: str, body: PriorityIn, db: DB, manager: Manager):
    """manager overrides the ai/keyword priority (saved as 'manual')"""
    return ComplaintOut.of(ComplaintService(db).override_priority(ticket_id, manager, body.priority))


@router.post("/{ticket_id}/reply-suggestion")
def reply_suggestion(ticket_id: str, db: DB, manager: Manager, llm: LLM):
    """an ai draft based on similar fixed complaints. nothing is saved or sent: the manager edits it"""
    hit(f"ai:{manager.id}", settings.ai_requests_per_hour, 3600)
    service = ComplaintService(db)
    complaint = service.get_for(manager, ticket_id)
    result = suggest_reply(db, llm, complaint)
    db.commit()     # only keeps the embedding if one was just made
    return result
