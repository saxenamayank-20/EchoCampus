from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.enums import Role
from backend.app.models import ManagerCategory, User


class UserRepository:
    """only talks to the db, no business rules here"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: str) -> User | None:
        return self.db.scalar(select(User).where(User.user_id == user_id))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def list_users(self, role: Role | None = None) -> list[User]:
        query = select(User).order_by(User.created_at.desc())
        if role:
            query = query.where(User.role == role)
        return list(self.db.scalars(query))

    def student_user_ids(self) -> list[str]:
        return list(self.db.scalars(select(User.user_id).where(User.role == Role.STUDENT)))

    def count(self, role: Role) -> int:
        return self.db.scalar(select(func.count()).select_from(User).where(User.role == role))

    def manager_for_category(self, category: str) -> User | None:
        return self.db.scalar(
            select(User).join(ManagerCategory).where(ManagerCategory.category == category))
