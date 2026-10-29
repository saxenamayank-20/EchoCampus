from fastapi import APIRouter, status

from backend.app.core.config import settings
from backend.app.core.deps import DB, CurrentUser, Sender
from backend.app.core.security import create_access_token
from backend.app.schemas.user import (LoginIn, MessageOut, RegisterIn, RegisterOut, TokenOut,
                                      UserIdIn, UserOut, VerifyOtpIn)
from backend.app.services.errors import NotFoundError
from backend.app.services.otp_service import OtpService
from backend.app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DB, sender: Sender):
    """creates an unverified student and emails a 6 digit code"""
    student = UserService(db).register_student(body.name, body.email, body.password, body.department)
    OtpService(db, sender).send(student)
    return RegisterOut(user_id=student.user_id,
                       message="Account created. Check your email for the 6 digit code.")


@router.post("/verify-otp", response_model=MessageOut)
def verify_otp(body: VerifyOtpIn, db: DB, sender: Sender):
    user = _find(db, body.user_id)
    OtpService(db, sender).verify(user, body.code)
    return MessageOut(message="Email verified. You can log in now.")


@router.post("/resend-otp", response_model=MessageOut)
def resend_otp(body: UserIdIn, db: DB, sender: Sender):
    OtpService(db, sender).send(_find(db, body.user_id))
    return MessageOut(message="A new code was sent to your email.")


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DB):
    user = UserService(db).authenticate(body.user_id, body.password)
    token = create_access_token(user.user_id, user.role.value)
    return TokenOut(access_token=token, expires_in=settings.jwt_expire_minutes * 60, user=UserOut.of(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut.of(user)


def _find(db, user_id: str):
    user = UserService(db).get(user_id.strip())
    if not user:
        raise NotFoundError("No account with that ID.")
    return user
