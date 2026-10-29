from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.core.deps import DB, CurrentUser
from backend.app.schemas.attachment import AttachmentOut
from backend.app.services.attachment_service import AttachmentService
from backend.app.services.storage import LocalStorage, get_storage

router = APIRouter(tags=["attachments"])

Storage = Annotated[LocalStorage, Depends(get_storage)]


@router.post("/complaints/{ticket_id}/attachments", response_model=AttachmentOut,
             status_code=status.HTTP_201_CREATED)
def upload(ticket_id: str, file: UploadFile, db: DB, user: CurrentUser, storage: Storage):
    """one file per request, so the frontend can show progress for each"""
    # read one byte more than the limit, enough to know it's too big without loading a huge file
    data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    attachment = AttachmentService(db, storage).upload(ticket_id, user, file.filename, data)
    return AttachmentOut.of(attachment)


@router.get("/complaints/{ticket_id}/attachments", response_model=list[AttachmentOut])
def list_files(ticket_id: str, db: DB, user: CurrentUser, storage: Storage):
    return [AttachmentOut.of(a) for a in AttachmentService(db, storage).list_for(user, ticket_id)]


@router.get("/attachments/{attachment_id}")
def download(attachment_id: int, db: DB, user: CurrentUser, storage: Storage, download: bool = False):
    """inline = open in the browser (preview), download=true = save as file"""
    attachment, path = AttachmentService(db, storage).open_for(user, attachment_id)
    return FileResponse(path, media_type=attachment.mime_type, filename=attachment.original_name,
                        content_disposition_type="attachment" if download else "inline",
                        headers={"X-Content-Type-Options": "nosniff"})
