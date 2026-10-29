from collections.abc import Callable, Iterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.enums import Role
from backend.app.core.security import decode_access_token
from backend.app.db.session import SessionLocal
from backend.app.models import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.email_service import EmailSender

bearer = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    """one session per request, closed when the request ends"""
    with SessionLocal() as db:
        yield db


def get_email_sender() -> EmailSender:
    return EmailSender()


DB = Annotated[Session, Depends(get_db)]


def get_current_user(db: DB,
                     creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    """reads 'Authorization: Bearer <token>' and returns that user"""
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again.") from None

    user = UserRepository(db).get_by_user_id(payload.get("sub", ""))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable[[User], User]:
    """use like Depends(require_role(Role.ADMIN))"""
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to this.")
        return user
    return checker


Student = Annotated[User, Depends(require_role(Role.STUDENT))]
Manager = Annotated[User, Depends(require_role(Role.MANAGER))]
Admin = Annotated[User, Depends(require_role(Role.ADMIN))]
Sender = Annotated[EmailSender, Depends(get_email_sender)]
