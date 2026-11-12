from fastapi import APIRouter, BackgroundTasks, status

from backend.app.core.cache import get_cache
from backend.app.core.config import settings
from backend.app.core.deps import DB, CurrentUser, Sender
from backend.app.core.enums import Role
from backend.app.core.rate_limit import hit
from backend.app.core.security import create_access_token
from backend.app.models import EmailOtp
from backend.app.schemas.user import (
    ChangePasswordIn,
    ChangePasswordOut,
    EmailIn,
    ForgotPasswordIn,
    LoginCodeIn,
    LoginIn,
    MessageOut,
    RegisterIn,
    RegisterOut,
    TokenOut,
    UserOut,
    VerifyOtpIn,
    VerifyOut,
)
from backend.app.services.email_templates import password_changed_email, welcome_email
from backend.app.services.errors import (
    AuthenticationError,
    ConflictError,
    EmailFailedError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
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
    subject, text, html = welcome_email(user.name, user.user_id, user.email)
    sender.send(user.email, subject, text, html)
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


@router.post("/change-password", response_model=ChangePasswordOut)
def change_password(body: ChangePasswordIn, db: DB, user: CurrentUser, sender: Sender, background: BackgroundTasks):
    # same limit as login, so a stolen token can't be used to guess the current password
    hit(f"pwchange:{user.user_id}", settings.rate_limit_logins_per_15_min, 15 * 60)
    # after a login code the email was just proven, so the old password isn't needed
    UserService(db).change_password(user, body.current_password, body.new_password, need_current=not user.code_login)
    subject, text, html = password_changed_email(user.name, user.email)
    background.add_task(sender.send, user.email, subject, text, html)
    # a login code session gets a normal token back, so the "set a new password" banner goes away
    token = create_access_token(user.user_id, user.role.value) if user.code_login else None
    return ChangePasswordOut(message="Password changed. Use the new one next time you sign in.", access_token=token)


# ── forgot details (students only) ───────────────────────────────────────────
SENT = "If a student account exists for this, we've sent a code to its email."
STAFF = "Staff accounts can't be recovered here. Please contact the admin or the technical team."


@router.post("/forgot/id", response_model=MessageOut)
def forgot_id(body: EmailIn, db: DB, sender: Sender):
    """forgot student id: a recovery code goes to that email"""
    user = UserService(db).users.get_by_email(body.email.strip().lower())
    _daily_limit(f"u{user.id}" if user else f"e{body.email.lower()}")
    if user and user.role != Role.STUDENT:
        raise PermissionDeniedError(STAFF)
    if user and user.is_verified and not OtpService(db, sender).send(user, "recovery"):
        raise EmailFailedError("We couldn't send the email right now. Please try again in a minute.")
    # same answer whether the account exists or not, so nobody can check emails here
    return MessageOut(message=SENT)


@router.post("/forgot/id/verify", response_model=VerifyOut)
def forgot_id_verify(body: VerifyOtpIn, db: DB):
    """right recovery code -> the student id"""
    user = UserService(db).users.get_by_email(body.email.strip().lower())
    if not user or user.role != Role.STUDENT or not user.is_verified:
        raise InvalidInputError("No active code. Ask for a new one.")
    OtpService(db, None).verify(user, body.code, "recovery")
    return VerifyOut(user_id=user.user_id, message="Here's your student ID.")


@router.post("/forgot/password", response_model=MessageOut)
def forgot_password(body: ForgotPasswordIn, db: DB, sender: Sender):
    """forgot password: a one-time login code goes to the account's email"""
    uid = body.user_id.strip()
    user = UserService(db).get(uid)
    _daily_limit(f"u{user.id}" if user else f"i{uid}")
    if user and user.role != Role.STUDENT:
        raise PermissionDeniedError(STAFF)
    if user and user.is_verified and not OtpService(db, sender).send(user, "login"):
        raise EmailFailedError("We couldn't send the email right now. Please try again in a minute.")
    return MessageOut(message=SENT)


@router.post("/login-code", response_model=TokenOut)
def login_with_code(body: LoginCodeIn, db: DB):
    """sign in with student id + login code instead of the password"""
    uid = body.user_id.strip()
    hit(f"login:{uid}", settings.rate_limit_logins_per_15_min, 15 * 60)
    user = UserService(db).get(uid)
    if not user or user.role != Role.STUDENT or not user.is_verified or not user.is_active:
        raise AuthenticationError("Invalid student ID or code.")
    OtpService(db, None).verify(user, body.code, "login")
    token = create_access_token(user.user_id, user.role.value, code_login=True)
    return TokenOut(access_token=token, expires_in=settings.jwt_expire_minutes * 60,
                    user=UserOut.of(user), code_login=True)


def _daily_limit(key: str) -> None:
    """recovery + login codes per account per day. after that a human has to help"""
    if get_cache().incr(f"rl:recover:{key}", 24 * 3600) > settings.recovery_codes_per_day:
        raise RateLimitError(f"You've asked for too many codes today. Please contact the technical team at "
                             f"{settings.support_contact()}.")


def _by_email(db, email: str):
    user = UserService(db).users.get_by_email(email.strip().lower())
    if not user:
        raise NotFoundError("No account with that email.")
    return user
