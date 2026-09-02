"""add persisted RSS feed sources

Revision ID: c4d9e8f1a2b3
Revises: 8f3c2d1e4a6b
Create Date: 2026-09-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d9e8f1a2b3"
down_revision: str | Sequence[str] | None = "8f3c2d1e4a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist RSS source configuration and article lineage."""
    op.create_table(
        "feed_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("feed_url", sa.String(length=2000), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "interval_minutes",
            sa.Integer(),
            server_default="15",
            nullable=False,
        ),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "interval_minutes BETWEEN 1 AND 1440",
            name="ck_feed_sources_interval_minutes",
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "brand_id",
            "feed_url",
            name="uq_feed_sources_brand_id_feed_url",
        ),
    )
    op.create_index(
        op.f("ix_feed_sources_brand_id"),
        "feed_sources",
        ["brand_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feed_sources_enabled"),
        "feed_sources",
        ["enabled"],
        unique=False,
    )
    op.add_column("articles", sa.Column("feed_source_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_articles_feed_source_id_feed_sources",
        "articles",
        "feed_sources",
        ["feed_source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_articles_feed_source_id"),
        "articles",
        ["feed_source_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove RSS source persistence."""
    op.drop_index(op.f("ix_articles_feed_source_id"), table_name="articles")
    op.drop_constraint(
        "fk_articles_feed_source_id_feed_sources",
        "articles",
        type_="foreignkey",
    )
    op.drop_column("articles", "feed_source_id")
    op.drop_index(op.f("ix_feed_sources_enabled"), table_name="feed_sources")
    op.drop_index(op.f("ix_feed_sources_brand_id"), table_name="feed_sources")
    op.drop_table("feed_sources")
