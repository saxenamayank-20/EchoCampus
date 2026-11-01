from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile, status
from pydantic import BaseModel, Field

from backend.app.ai.rag import answer_question
from backend.app.core.config import settings
from backend.app.core.deps import DB, LLM, Admin, CurrentUser
from backend.app.core.rate_limit import hit
from backend.app.models import PolicyDocument
from backend.app.schemas.user import MessageOut
from backend.app.services.policy_service import MAX_POLICY_MB, PolicyService
from backend.app.services.storage import LocalStorage, get_storage

router = APIRouter(tags=["policies"])
Storage = Annotated[LocalStorage, Depends(get_storage)]


class PolicyOut(BaseModel):
    id: int
    title: str
    filename: str
    pages: int
    chunks: int
    uploaded_by: str
    updated_at: datetime

    @classmethod
    def of(cls, d: PolicyDocument) -> "PolicyOut":
        return cls(id=d.id, title=d.title, filename=d.filename, pages=d.pages, chunks=len(d.chunks),
                   uploaded_by=d.uploader.user_id, updated_at=d.updated_at)


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class SourceOut(BaseModel):
    n: int
    document: str
    page: int
    snippet: str


class AskOut(BaseModel):
    answered: bool
    answer: str
    sources: list[SourceOut]
    suggested_title: str | None = None   # prefill for "raise a complaint" when not answered


def _read(file: UploadFile) -> bytes:
    return file.file.read(MAX_POLICY_MB * 1024 * 1024 + 1)


@router.get("/admin/policies", response_model=list[PolicyOut])
def list_policies(db: DB, _: Admin, llm: LLM, storage: Storage):
    return [PolicyOut.of(d) for d in PolicyService(db, llm, storage).all_policies()]


@router.post("/admin/policies", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def upload_policy(title: Annotated[str, Form(max_length=200)], file: UploadFile, db: DB, admin: Admin,
                  llm: LLM, storage: Storage):
    return PolicyOut.of(PolicyService(db, llm, storage).upload(admin, title, file.filename, _read(file)))


@router.put("/admin/policies/{doc_id}", response_model=PolicyOut)
def replace_policy(doc_id: int, file: UploadFile, db: DB, admin: Admin, llm: LLM, storage: Storage):
    """re-upload: old chunks are replaced by the new pdf's"""
    return PolicyOut.of(PolicyService(db, llm, storage).replace(admin, doc_id, file.filename, _read(file)))


@router.delete("/admin/policies/{doc_id}", response_model=MessageOut)
def delete_policy(doc_id: int, db: DB, admin: Admin, llm: LLM, storage: Storage):
    PolicyService(db, llm, storage).delete(admin, doc_id)
    return MessageOut(message="Policy deleted.")


@router.post("/assistant/ask", response_model=AskOut)
def ask(body: AskIn, db: DB, user: CurrentUser, llm: LLM):
    """answers only from the uploaded policies, with page citations"""
    hit(f"ai:{user.id}", settings.ai_requests_per_hour, 3600)
    return AskOut(**answer_question(db, llm, body.question))
