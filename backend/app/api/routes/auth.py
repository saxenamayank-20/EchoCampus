from fastapi import APIRouter, status

from backend.app.core.config import settings
from backend.app.core.deps import DB, CurrentUser, Sender
from backend.app.core.rate_limit import hit
from backend.app.core.security import create_access_token
from backend.app.models import EmailOtp
from backend.app.schemas.user import (
    ChangePasswordIn,
    EmailIn,
    LoginIn,
    MessageOut,
    RegisterIn,
    RegisterOut,
    TokenOut,
    UserOut,
    VerifyOtpIn,
    VerifyOut,
)
from backend.app.services.errors import ConflictError, EmailFailedError, NotFoundError
from backend.app.services.otp_service import OtpService
from backend.app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DB, sender: Sender):
    """creates an unverified student and emails a 6 digit code. the id comes after verifying"""
    student = UserService(db).register_student(body.name, body.email, body.password, body.department)
    if not OtpService(db, sender).send(student):
        # no code means they could never verify, so drop the account and let them try again
        db.query(EmailOtp).filter(EmailOtp.user_id == student.id).delete()
        db.delete(student)
        db.commit()
        raise EmailFailedError("We couldn't send the email right now. Please try again in a minute.")
    return RegisterOut(email=student.email, message="Check your email for the 6 digit code.")


@router.post("/verify-otp", response_model=VerifyOut)
def verify_otp(body: VerifyOtpIn, db: DB, sender: Sender):
    user = _by_email(db, body.email)
    if user.is_verified:
        # don't hand out the id again to someone who only knows the email
        raise ConflictError("This email is already verified. Log in with your student ID.")
    OtpService(db, sender).verify(user, body.code)
    # keep a copy of the id in their inbox, in case they close the page
    sender.send(user.email, "Your EchoCampus student ID",
                f"Hi {user.name},\n\nYour email is verified. Your student ID is {user.user_id}.\n"
                f"You need it with your password to log in.")
    return VerifyOut(user_id=user.user_id, message="Email verified. You can log in now.")


@router.post("/resend-otp", response_model=MessageOut)
def resend_otp(body: EmailIn, db: DB, sender: Sender):
    # stops someone from flooding a student's inbox
    hit(f"otp:{body.email.lower()}", 5, 15 * 60)
    if not OtpService(db, sender).send(_by_email(db, body.email)):
        raise EmailFailedError("We couldn't send the email right now. Please try again in a minute.")
    return MessageOut(message="A new code was sent to your email.")


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DB):
    # slows down password guessing: max 10 tries per 15 minutes for one user id.
    # not per ip, on render every request comes from the proxy's ip so all users would share one limit
    hit(f"login:{body.user_id.strip().upper()}", settings.rate_limit_logins_per_15_min, 15 * 60)
    user = UserService(db).authenticate(body.user_id, body.password)
    token = create_access_token(user.user_id, user.role.value)
    return TokenOut(access_token=token, expires_in=settings.jwt_expire_minutes * 60, user=UserOut.of(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut.of(user)


@router.post("/change-password", response_model=MessageOut)
def change_password(body: ChangePasswordIn, db: DB, user: CurrentUser):
    # same limit as login, so a stolen token can't be used to guess the current password
    hit(f"pwchange:{user.user_id}", settings.rate_limit_logins_per_15_min, 15 * 60)
    UserService(db).change_password(user, body.current_password, body.new_password)
    return MessageOut(message="Password changed. Use the new one next time you sign in.")


def _by_email(db, email: str):
    user = UserService(db).users.get_by_email(email.strip().lower())
    if not user:
        raise NotFoundError("No account with that email.")
    return user
