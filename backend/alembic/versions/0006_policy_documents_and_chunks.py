"""policy documents and chunks

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-01

Phase 4.2: policy_documents (the admin's pdfs) and policy_chunks (~450-word pieces with
their embedding), plus an HNSW index on postgres for fast policy search.
"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('policy_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('stored_name', sa.String(length=64), nullable=False),
    sa.Column('pages', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], name=op.f('fk_policy_documents_uploaded_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_policy_documents'))
    )
    op.create_table('policy_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['policy_documents.id'], name=op.f('fk_policy_chunks_document_id_policy_documents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_policy_chunks'))
    )
    with op.batch_alter_table('policy_chunks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_policy_chunks_document_id'), ['document_id'], unique=False)

    if op.get_bind().dialect.name == "postgresql":
        op.create_index("ix_policy_chunks_embedding_hnsw", "policy_chunks", ["embedding"], postgresql_using="hnsw",
                        postgresql_with={"m": 16, "ef_construction": 64},
                        postgresql_ops={"embedding": "vector_cosine_ops"})


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_policy_chunks_embedding_hnsw", table_name="policy_chunks")
    with op.batch_alter_table('policy_chunks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_policy_chunks_document_id'))

    op.drop_table('policy_chunks')
    op.drop_table('policy_documents')
