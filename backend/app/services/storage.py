import uuid
from pathlib import Path

from backend.app.core.config import settings


class LocalStorage:
    """saves files in a local folder. at deployment a cloud storage class with the same methods replaces it"""

    def __init__(self, base_dir: str):
        self.base = Path(base_dir)

    def save(self, data: bytes, extension: str) -> str:
        # random name, the user's file name never touches the disk
        name = f"{uuid.uuid4().hex}{extension}"
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / name).write_bytes(data)
        return name

    def path(self, stored_name: str) -> Path:
        return self.base / stored_name

    def delete(self, stored_name: str) -> None:
        self.path(stored_name).unlink(missing_ok=True)


def get_storage() -> LocalStorage:
    return LocalStorage(settings.upload_dir)
