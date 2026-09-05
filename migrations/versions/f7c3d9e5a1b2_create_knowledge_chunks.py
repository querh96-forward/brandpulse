"""create knowledge chunks

Revision ID: f7c3d9e5a1b2
Revises: e6b2c8d4f0a1
Create Date: 2026-09-04 00:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "f7c3d9e5a1b2"
down_revision: str | Sequence[str] | None = "e6b2c8d4f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create brand-scoped knowledge chunks with 1024-dimensional embeddings."""
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("section_title", sa.String(length=500), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding", Vector(dim=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_chunk_index"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "brand_id",
            "content_hash",
            name="uq_knowledge_chunks_brand_content_hash",
        ),
    )
    op.create_index(
        op.f("ix_knowledge_chunks_brand_id"),
        "knowledge_chunks",
        ["brand_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_chunks_source_name"),
        "knowledge_chunks",
        ["source_name"],
        unique=False,
    )


def downgrade() -> None:
    """Drop knowledge chunks while leaving the pgvector extension available."""
    op.drop_index(op.f("ix_knowledge_chunks_source_name"), table_name="knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_chunks_brand_id"), table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
