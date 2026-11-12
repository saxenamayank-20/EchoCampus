"""otp purpose

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-12

forgot details: email codes now have a purpose (verify, recovery, login),
so a recovery code can't be used to log in.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # old rows were all email verification codes
    op.add_column('email_otps', sa.Column('purpose', sa.String(length=20), nullable=False, server_default='verify'))


def downgrade() -> None:
    op.drop_column('email_otps', 'purpose')
