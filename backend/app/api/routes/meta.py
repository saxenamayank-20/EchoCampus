from fastapi import APIRouter

from backend.app.core.constants import CATEGORIES

router = APIRouter(tags=["meta"])


@router.get("/meta/categories", response_model=list[str])
def categories():
    return CATEGORIES


@router.get("/health")
def health():
    return {"status": "ok"}
