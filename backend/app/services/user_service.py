from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.constants import STUDENT_ID_PREFIX, STUDENT_ID_START
from backend.app.core.enums import Role
from backend.app.core.security import hash_password, validate_password, verify_password
from backend.app.models import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.errors import (AuthenticationError, ConflictError, InvalidInputError,
                                         NotVerifiedError)


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def next_student_id(self) -> str:
        """ST000101, ST000102 ... (max + 1 is fine on sqlite, phase 3 moves this to a postgres sequence)"""
        numbers = [int(uid[len(STUDENT_ID_PREFIX):]) for uid in self.users.student_user_ids()
                   if uid[len(STUDENT_ID_PREFIX):].isdigit()]
        next_number = max(numbers, default=STUDENT_ID_START - 1) + 1
        return f"{STUDENT_ID_PREFIX}{next_number:06d}"

    def register_student(self, name: str, email: str, password: str, department: str) -> User:
        name, email = name.strip(), email.strip().lower()
        if not name or not email:
            raise InvalidInputError("Name and email are required.")
        domains = settings.email_domains()
        if domains and email.rsplit("@", 1)[-1] not in domains:
            raise InvalidInputError(f"Use your college email ({', '.join(domains)}).")
        ok, message = validate_password(password)
        if not ok:
            raise InvalidInputError(message)
        if self.users.get_by_email(email):
            raise ConflictError("Email already registered.")

        student = User(user_id=self.next_student_id(), name=name, email=email,
                       password_hash=hash_password(password), role=Role.STUDENT,
                       department=department)
        self.users.add(student)
        self.db.commit()
        return student

    def login(self, user_id: str, password: str) -> User | None:
        user = self.users.get_by_user_id(user_id.strip())
        if user and user.is_active and verify_password(password, user.password_hash):
            return user
        return None

    def authenticate(self, user_id: str, password: str) -> User:
        """login for the api: wrong details -> 401, email not verified -> 403"""
        user = self.login(user_id, password)
        if not user:
            raise AuthenticationError("Invalid user ID or password.")
        if not user.is_verified:
            raise NotVerifiedError("Please verify your email first.")
        return user

    def get(self, user_id: str) -> User | None:
        return self.users.get_by_user_id(user_id)

    def list_users(self, role: Role | None = None) -> list[User]:
        return self.users.list_users(role)
