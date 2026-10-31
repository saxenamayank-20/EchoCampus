"""sla fields and notifications

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31

Adds sla_due_at / escalated / escalated_at to complaints and the notifications table (bell icon).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('complaint_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.String(length=30), nullable=False),
    sa.Column('message', sa.String(length=300), nullable=False),
    sa.Column('is_read', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_notifications_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index('ix_notifications_user_read', ['user_id', 'is_read'], unique=False)

    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sla_due_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('escalated', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('escalated_at', sa.DateTime(), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.drop_column('escalated_at')
        batch_op.drop_column('escalated')
        batch_op.drop_column('sla_due_at')

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index('ix_notifications_user_read')

    op.drop_table('notifications')
