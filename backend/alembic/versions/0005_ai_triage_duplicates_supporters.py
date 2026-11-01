"""ai triage duplicates supporters

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-01

Phase 4.1: llm_calls (every ai call), complaint_supporters ("I have this issue too"),
complaints.ai_summary / embedding (768 numbers) / duplicate_of, and on postgres an
HNSW index so "most similar complaints" is fast.
"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('llm_calls',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('feature', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=60), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=True),
    sa.Column('output_tokens', sa.Integer(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('error', sa.String(length=300), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_llm_calls'))
    )
    op.create_table('complaint_supporters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('complaint_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], name=op.f('fk_complaint_supporters_complaint_id_complaints')),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_complaint_supporters_student_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_supporters')),
    sa.UniqueConstraint('complaint_id', 'student_id', name='uq_supporter_pair')
    )
    with op.batch_alter_table('complaint_supporters', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_complaint_supporters_complaint_id'), ['complaint_id'], unique=False)

    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ai_summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=True))
        batch_op.add_column(sa.Column('duplicate_of', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_complaints_duplicate_of_complaints'), 'complaints', ['duplicate_of'], ['id'])

    if op.get_bind().dialect.name == "postgresql":
        # hnsw = a graph index for fast nearest-neighbour search, using cosine distance
        op.create_index("ix_complaints_embedding_hnsw", "complaints", ["embedding"], postgresql_using="hnsw",
                        postgresql_with={"m": 16, "ef_construction": 64},
                        postgresql_ops={"embedding": "vector_cosine_ops"})


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_complaints_embedding_hnsw", table_name="complaints")
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_complaints_duplicate_of_complaints'), type_='foreignkey')
        batch_op.drop_column('duplicate_of')
        batch_op.drop_column('embedding')
        batch_op.drop_column('ai_summary')

    with op.batch_alter_table('complaint_supporters', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_complaint_supporters_complaint_id'))

    op.drop_table('complaint_supporters')
    op.drop_table('llm_calls')
