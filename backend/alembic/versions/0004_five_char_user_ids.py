"""five character user ids

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-01

Staff ids become 5 characters: ADMIN001 -> AD100, GM001 -> GM101 ... GM004 -> GM104.
Students were ST000101 style, they become ST101 (same number, fewer zeros).
Only data changes here, the table structure stays the same.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAFF = {"ADMIN001": "AD100", "GM001": "GM101", "GM002": "GM102", "GM003": "GM103", "GM004": "GM104"}


def _rename(pairs: dict[str, str]) -> None:
    users = sa.table("users", sa.column("user_id", sa.String))
    for old, new in pairs.items():
        op.execute(users.update().where(users.c.user_id == old).values(user_id=new))


def upgrade() -> None:
    _rename(STAFF)
    # ST000101 -> ST101 (keep the number, drop the extra zeros)
    bind = op.get_bind()
    for (uid,) in bind.execute(sa.text("SELECT user_id FROM users WHERE user_id LIKE 'ST0%'")).fetchall():
        _rename({uid: f"ST{int(uid[2:]):03d}"})


def downgrade() -> None:
    _rename({new: old for old, new in STAFF.items()})
    bind = op.get_bind()
    for (uid,) in bind.execute(sa.text("SELECT user_id FROM users WHERE user_id LIKE 'ST%'")).fetchall():
        if len(uid) == 5:
            _rename({uid: f"ST{int(uid[2:]):06d}"})
