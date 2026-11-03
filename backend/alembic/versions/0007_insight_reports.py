"""insight reports

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-03

Phase 5: insight_reports, the weekly ai report for the admin and the numbers it was written from.
(langgraph's checkpoint tables are not here: langgraph creates them itself on startup)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('insight_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('period_start', sa.DateTime(), nullable=False),
    sa.Column('period_end', sa.DateTime(), nullable=False),
    sa.Column('stats', sa.Text(), nullable=False),
    sa.Column('report', sa.Text(), nullable=False),
    sa.Column('used_ai', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_insight_reports_created_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_insight_reports'))
    )
    op.create_index(op.f('ix_insight_reports_created_at'), 'insight_reports', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_insight_reports_created_at'), table_name='insight_reports')
    op.drop_table('insight_reports')
