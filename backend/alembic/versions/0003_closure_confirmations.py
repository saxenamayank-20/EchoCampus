"""closure confirmations

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31

The table for the student confirmation loop (one row per close request round).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('closure_confirmations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('complaint_id', sa.Integer(), nullable=False),
    sa.Column('requested_by', sa.Integer(), nullable=False),
    sa.Column('manager_note', sa.Text(), nullable=False),
    sa.Column('student_response', sa.String(length=20), nullable=False),
    sa.Column('student_reason', sa.Text(), nullable=True),
    sa.Column('rating', sa.Integer(), nullable=True),
    sa.Column('due_at', sa.DateTime(), nullable=False),
    sa.Column('responded_at', sa.DateTime(), nullable=True),
    sa.Column('reminder_sent', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('admin_decision', sa.String(length=20), nullable=True),
    sa.Column('admin_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_closure_confirmations_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], name=op.f('fk_closure_confirmations_requested_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_closure_confirmations'))
    )
    with op.batch_alter_table('closure_confirmations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_closure_confirmations_complaint_id'), ['complaint_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('closure_confirmations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_closure_confirmations_complaint_id'))

    op.drop_table('closure_confirmations')
