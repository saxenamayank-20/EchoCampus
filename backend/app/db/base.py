from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """parent class of every table"""


def now() -> datetime:
    return datetime.now()


def enum_column(enum_cls: type[StrEnum]) -> Enum:
    # save the value ("In Progress"), not the python name ("IN_PROGRESS")
    return Enum(enum_cls, values_callable=lambda e: [m.value for m in e],
                native_enum=False, length=30)
