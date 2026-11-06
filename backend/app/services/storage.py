import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models import StoredFile


class DatabaseStorage:
    """keeps uploaded files in postgres (stored_files), so they survive a restart on render.
    uses the request's own session: the file and its attachment row are saved in one commit"""

    def __init__(self, db: Session):
        self.db = db

    def save(self, data: bytes, extension: str) -> str:
        # random name, the user's file name is never used for storage
        name = f"{uuid.uuid4().hex}{extension}"
        self.db.add(StoredFile(name=name, data=data, size_bytes=len(data)))
        return name

    def read(self, stored_name: str) -> bytes | None:
        return self.db.scalar(select(StoredFile.data).where(StoredFile.name == stored_name))

    def delete(self, stored_name: str) -> None:
        self.db.execute(delete(StoredFile).where(StoredFile.name == stored_name))
