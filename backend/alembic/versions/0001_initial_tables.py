"""initial tables

Revision ID: 0001
Revises:
Create Date: 2026-10-31

All Phase 1-2 tables, plus the postgres extras: enum types, the student id
sequence and the pgvector extension (used by the ai part in phase 4).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: each type is made once below, not again by every table that uses it.
# on sqlite these just become text columns
ROLE = postgresql.ENUM("student", "grievance_manager", "admin", name="role", create_type=False)
STATUS = postgresql.ENUM("Pending", "Assigned", "In Progress", "Resolved", "Closed", name="status", create_type=False)
PRIORITY = postgresql.ENUM("Critical", "High", "Medium", "Low", name="priority", create_type=False)
STUDENT_ID_SEQ = sa.Sequence("student_id_seq", start=101)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        for enum in (ROLE, STATUS, PRIORITY):
            enum.create(bind, checkfirst=True)
        op.execute(sa.schema.CreateSequence(STUDENT_ID_SEQ))

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', ROLE, nullable=False),
    sa.Column('department', sa.String(length=100), nullable=True),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    sa.UniqueConstraint('user_id', name=op.f('uq_users_user_id'))
    )
    op.create_table('complaints',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket_id', sa.String(length=20), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('priority', PRIORITY, nullable=False),
    sa.Column('priority_source', sa.String(length=10), nullable=False),
    sa.Column('status', STATUS, nullable=False),
    sa.Column('assigned_to', sa.Integer(), nullable=True),
    sa.Column('student_remarks', sa.Text(), nullable=True),
    sa.Column('manager_remarks', sa.Text(), nullable=True),
    sa.Column('meet_link', sa.String(length=255), nullable=True),
    sa.Column('close_requested', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], name=op.f('fk_complaints_assigned_to_users')),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_complaints_student_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaints')),
    sa.UniqueConstraint('ticket_id', name=op.f('uq_complaints_ticket_id'))
    )
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.create_index('ix_complaints_assigned_status', ['assigned_to', 'status'], unique=False)
        batch_op.create_index('ix_complaints_status_created', ['status', 'created_at'], unique=False)

    op.create_table('email_otps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_email_otps_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_email_otps'))
    )
    op.create_table('manager_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('manager_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['manager_id'], ['users.id'], name=op.f('fk_manager_categories_manager_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_manager_categories')),
    sa.UniqueConstraint('category', name=op.f('uq_manager_categories_category'))
    )
    op.create_table('attachments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('complaint_id', sa.Integer(), nullable=False),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('stored_name', sa.String(length=64), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_attachments_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], name=op.f('fk_attachments_uploaded_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attachments')),
    sa.UniqueConstraint('stored_name', name=op.f('uq_attachments_stored_name'))
    )
    with op.batch_alter_table('attachments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_attachments_complaint_id'), ['complaint_id'], unique=False)

    op.create_table('complaint_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('complaint_id', sa.Integer(), nullable=False),
    sa.Column('changed_by', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('old_status', STATUS, nullable=True),
    sa.Column('new_status', STATUS, nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_complaint_history_changed_by_users')),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_complaint_history_complaint_id_complaints')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_history'))
    )
    op.create_table('manager_updates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('complaint_id', sa.Integer(), nullable=False),
    sa.Column('manager_id', sa.Integer(), nullable=False),
    sa.Column('update_text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_manager_updates_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['manager_id'], ['users.id'], name=op.f('fk_manager_updates_manager_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_manager_updates'))
    )


def downgrade() -> None:
    op.drop_table('manager_updates')
    op.drop_table('complaint_history')
    with op.batch_alter_table('attachments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_attachments_complaint_id'))

    op.drop_table('attachments')
    op.drop_table('manager_categories')
    op.drop_table('email_otps')
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.drop_index('ix_complaints_status_created')
        batch_op.drop_index('ix_complaints_assigned_status')

    op.drop_table('complaints')
    op.drop_table('users')
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.schema.DropSequence(STUDENT_ID_SEQ))
        for enum in (PRIORITY, STATUS, ROLE):
            enum.drop(bind, checkfirst=True)
