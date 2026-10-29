from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.enums import Role, Status
from backend.app.models import Attachment, User
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.errors import (InvalidInputError, NotFoundError, PermissionDeniedError,
                                         TooLargeError, UnsupportedFileError)
from backend.app.services.file_types import detect_file_type
from backend.app.services.storage import LocalStorage


class AttachmentService:
    def __init__(self, db: Session, storage: LocalStorage):
        self.db = db
        self.storage = storage
        self.complaints = ComplaintService(db)

    def upload(self, ticket_id: str, uploader: User, filename: str, data: bytes) -> Attachment:
        # get_for already blocks anyone who can't see the complaint
        complaint = self.complaints.get_for(uploader, ticket_id)
        if uploader.role == Role.ADMIN:
            raise PermissionDeniedError("Only the student and the assigned manager can add proof.")
        if complaint.status == Status.CLOSED:
            raise InvalidInputError("This complaint is closed.")

        if not data:
            raise InvalidInputError("The file is empty.")
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise TooLargeError(f"Max file size is {settings.max_upload_mb} MB.")
        count = self.db.scalar(select(func.count()).select_from(Attachment)
                               .where(Attachment.complaint_id == complaint.id))
        if count >= settings.max_files_per_complaint:
            raise InvalidInputError(f"Max {settings.max_files_per_complaint} files per complaint.")

        kind = detect_file_type(data)
        if not kind:
            raise UnsupportedFileError("Only JPG, PNG, WEBP images, PDF and DOCX files are allowed.")
        mime, extension = kind

        stored = self.storage.save(data, extension)
        attachment = Attachment(complaint=complaint, original_name=_clean_name(filename),
                                stored_name=stored, mime_type=mime, size_bytes=len(data),
                                uploader=uploader)
        self.db.add(attachment)
        self.db.commit()
        return attachment

    def list_for(self, viewer: User, ticket_id: str) -> list[Attachment]:
        complaint = self.complaints.get_for(viewer, ticket_id)
        return list(self.db.scalars(select(Attachment).where(Attachment.complaint_id == complaint.id)
                                    .order_by(Attachment.id)))

    def open_for(self, viewer: User, attachment_id: int) -> tuple[Attachment, Path]:
        attachment = self.db.get(Attachment, attachment_id)
        if not attachment:
            raise NotFoundError("File not found.")
        # same rule as the complaint: owner student, assigned manager or admin
        self.complaints.get_for(viewer, attachment.complaint.ticket_id)
        path = self.storage.path(attachment.stored_name)
        if not path.exists():
            raise NotFoundError("File is missing from storage.")
        return attachment, path


def _clean_name(filename: str | None) -> str:
    """drop any folder part like ../../etc, keep just the name for display"""
    name = Path(filename or "file").name.strip() or "file"
    return name[:200]
