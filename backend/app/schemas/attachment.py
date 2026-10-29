from datetime import datetime

from pydantic import BaseModel

from backend.app.models import Attachment


class AttachmentOut(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    uploaded_by: str
    uploader_role: str
    created_at: datetime

    @classmethod
    def of(cls, a: Attachment) -> "AttachmentOut":
        return cls(id=a.id, original_name=a.original_name, mime_type=a.mime_type,
                   size_bytes=a.size_bytes, uploaded_by=a.uploader.user_id,
                   uploader_role=a.uploader.role.value, created_at=a.created_at)
