from urllib.parse import quote

from fastapi import APIRouter, UploadFile, status
from fastapi.responses import Response

from backend.app.core.config import settings
from backend.app.core.deps import DB, CurrentUser
from backend.app.schemas.attachment import AttachmentOut
from backend.app.services.attachment_service import AttachmentService

router = APIRouter(tags=["attachments"])


@router.post("/complaints/{ticket_id}/attachments", response_model=AttachmentOut,
             status_code=status.HTTP_201_CREATED)
def upload(ticket_id: str, file: UploadFile, db: DB, user: CurrentUser):
    """one file per request, so the frontend can show progress for each"""
    # read one byte more than the limit, enough to know it's too big without loading a huge file
    data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    attachment = AttachmentService(db).upload(ticket_id, user, file.filename, data)
    return AttachmentOut.of(attachment)


@router.get("/complaints/{ticket_id}/attachments", response_model=list[AttachmentOut])
def list_files(ticket_id: str, db: DB, user: CurrentUser):
    return [AttachmentOut.of(a) for a in AttachmentService(db).list_for(user, ticket_id)]


@router.get("/attachments/{attachment_id}")
def download(attachment_id: int, db: DB, user: CurrentUser, download: bool = False):
    """inline = open in the browser (preview), download=true = save as file"""
    attachment, data = AttachmentService(db).open_for(user, attachment_id)
    kind = "attachment" if download else "inline"
    return Response(data, media_type=attachment.mime_type,
                    headers={"Content-Disposition": f"{kind}; filename*=UTF-8''{quote(attachment.original_name)}",
                             "X-Content-Type-Options": "nosniff"})
