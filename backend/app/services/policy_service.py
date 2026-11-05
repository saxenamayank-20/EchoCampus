from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.ai.chunking import chunk_pages
from backend.app.ai.embeddings import policy_chunk_text
from backend.app.ai.llm_client import LLMClient, LLMError
from backend.app.ai.pdf import extract_pages
from backend.app.core.enums import Role
from backend.app.models import PolicyChunk, PolicyDocument, User
from backend.app.services.errors import (
    AIUnavailableError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    TooLargeError,
    UnsupportedFileError,
)
from backend.app.services.file_types import detect_file_type
from backend.app.services.storage import LocalStorage

MAX_POLICY_MB = 10


class PolicyService:
    """admin's policy pdfs: read the text, cut into chunks, embed, store"""

    def __init__(self, db: Session, llm: LLMClient, storage: LocalStorage):
        self.db = db
        self.llm = llm
        self.storage = storage

    def upload(self, admin: User, title: str, filename: str, data: bytes) -> PolicyDocument:
        self._check_admin(admin)
        pages = self._read(data)
        doc = PolicyDocument(title=title.strip()[:200] or filename, filename=(filename or "policy.pdf")[:255],
                             stored_name=self.storage.save(data, ".pdf"), pages=len(pages), uploader=admin)
        self.db.add(doc)
        self._index(doc, pages)
        self.db.commit()
        return doc

    def replace(self, admin: User, doc_id: int, filename: str, data: bytes) -> PolicyDocument:
        """re-upload: the old chunks are deleted and the new pdf is indexed"""
        self._check_admin(admin)
        doc = self._get(doc_id)
        pages = self._read(data)
        self.db.execute(delete(PolicyChunk).where(PolicyChunk.document_id == doc.id))
        self.db.expire(doc, ["chunks"])
        old_file = doc.stored_name
        doc.stored_name = self.storage.save(data, ".pdf")
        doc.filename = (filename or doc.filename)[:255]
        doc.pages = len(pages)
        self._index(doc, pages)
        self.db.commit()
        self.storage.delete(old_file)
        return doc

    def delete(self, admin: User, doc_id: int) -> None:
        self._check_admin(admin)
        doc = self._get(doc_id)
        self.storage.delete(doc.stored_name)
        self.db.delete(doc)
        self.db.commit()

    def all_policies(self) -> list[PolicyDocument]:
        return list(self.db.scalars(select(PolicyDocument).order_by(PolicyDocument.title)))

    # ── helpers ───────────────────────────────────────────────────────────────
    def _read(self, data: bytes) -> list[str]:
        if len(data) > MAX_POLICY_MB * 1024 * 1024:
            raise TooLargeError(f"Max policy size is {MAX_POLICY_MB} MB.")
        kind = detect_file_type(data)
        if not kind or kind[0] != "application/pdf":
            raise UnsupportedFileError("Policies must be PDF files.")
        pages = extract_pages(data)
        if not any(p.strip() for p in pages):
            raise InvalidInputError("No text found in this PDF (scanned images can't be read).")
        return pages

    def _index(self, doc: PolicyDocument, pages: list[str]) -> None:
        chunks = chunk_pages(pages)
        try:
            vectors = self.llm.embed("embedding", [policy_chunk_text(doc.title, c.text) for c in chunks])
        except LLMError as e:
            self.db.rollback()
            raise AIUnavailableError("AI is unavailable, the policy couldn't be indexed. Try again later.") from e
        for c, v in zip(chunks, vectors, strict=True):
            self.db.add(PolicyChunk(document=doc, chunk_index=c.index, page=c.page, content=c.text, embedding=v))

    def _get(self, doc_id: int) -> PolicyDocument:
        doc = self.db.get(PolicyDocument, doc_id)
        if not doc:
            raise NotFoundError("Policy not found.")
        return doc

    @staticmethod
    def _check_admin(user: User) -> None:
        if user.role != Role.ADMIN:
            raise PermissionDeniedError("Only the admin manages policies.")
