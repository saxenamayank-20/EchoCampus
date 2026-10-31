from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, MetaData
from sqlalchemy.orm import DeclarativeBase

# fixed names for keys and indexes, so alembic can find and change them later
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """parent class of every table"""

    metadata = MetaData(naming_convention=NAMING)


def now() -> datetime:
    return datetime.now()


def enum_column(enum_cls: type[StrEnum]) -> Enum:
    # a real enum type on postgres (role, status, priority), plain text on sqlite.
    # saves the value ("In Progress"), not the python name ("IN_PROGRESS")
    return Enum(enum_cls, name=enum_cls.__name__.lower(),
                values_callable=lambda e: [m.value for m in e])
