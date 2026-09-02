"""add RSS collection article limit

Revision ID: d5a1b7c3e9f2
Revises: c4d9e8f1a2b3
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5a1b7c3e9f2"
down_revision: str | Sequence[str] | None = "c4d9e8f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Limit the number of feed entries considered by each collection."""
    op.add_column(
        "feed_sources",
        sa.Column(
            "max_articles_per_collection",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_feed_sources_max_articles_per_collection",
        "feed_sources",
        "max_articles_per_collection BETWEEN 1 AND 50",
    )


def downgrade() -> None:
    """Remove the per-collection article limit."""
    op.drop_constraint(
        "ck_feed_sources_max_articles_per_collection",
        "feed_sources",
        type_="check",
    )
    op.drop_column("feed_sources", "max_articles_per_collection")
