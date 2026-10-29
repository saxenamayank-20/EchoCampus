from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from backend.app.models import User


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str
    department: str = Field(min_length=1, max_length=100)


class RegisterOut(BaseModel):
    user_id: str
    message: str


class VerifyOtpIn(BaseModel):
    user_id: str
    code: str = Field(pattern=r"^\d{6}$")


class UserIdIn(BaseModel):
    user_id: str


class LoginIn(BaseModel):
    user_id: str
    password: str


class UserOut(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    department: str | None
    categories: list[str]
    is_verified: bool
    created_at: datetime

    @classmethod
    def of(cls, u: User) -> "UserOut":
        return cls(user_id=u.user_id, name=u.name, email=u.email, role=u.role.value,
                   department=u.department, categories=[c.category for c in u.categories],
                   is_verified=u.is_verified, created_at=u.created_at)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds
    user: UserOut


class MessageOut(BaseModel):
    message: str
