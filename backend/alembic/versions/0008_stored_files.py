"""stored files

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-06

Phase 6: uploaded files (proof attachments, policy pdfs) are kept in postgres,
because render's free disk is wiped on every restart.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('stored_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stored_files')),
    sa.UniqueConstraint('name', name=op.f('uq_stored_files_name'))
    )


def downgrade() -> None:
    op.drop_table('stored_files')
