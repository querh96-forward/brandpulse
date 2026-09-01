"""enforce one active analysis job per article

Revision ID: 8f3c2d1e4a6b
Revises: 0715c85acf85
Create Date: 2026-08-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f3c2d1e4a6b"
down_revision: str | Sequence[str] | None = "0715c85acf85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow at most one queued or processing job per article."""
    op.create_index(
        "uq_analysis_jobs_active_article_id",
        "analysis_jobs",
        ["article_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'processing')"),
    )


def downgrade() -> None:
    """Remove the active-job uniqueness guarantee."""
    op.drop_index(
        "uq_analysis_jobs_active_article_id",
        table_name="analysis_jobs",
    )
