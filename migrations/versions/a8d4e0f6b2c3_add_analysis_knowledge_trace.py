"""add analysis knowledge trace

Revision ID: a8d4e0f6b2c3
Revises: f7c3d9e5a1b2
Create Date: 2026-09-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a8d4e0f6b2c3"
down_revision: str | Sequence[str] | None = "f7c3d9e5a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist the knowledge evidence used by each analysis."""
    op.add_column(
        "analysis_results",
        sa.Column(
            "knowledge_used",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "analysis_results",
        sa.Column(
            "knowledge_citations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "analysis_results",
        sa.Column("retrieval_model_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "analysis_results",
        sa.Column("evidence_model_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "analysis_results",
        sa.Column("evidence_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove persisted knowledge evidence from analysis results."""
    op.drop_column("analysis_results", "evidence_reason")
    op.drop_column("analysis_results", "evidence_model_name")
    op.drop_column("analysis_results", "retrieval_model_name")
    op.drop_column("analysis_results", "knowledge_citations")
    op.drop_column("analysis_results", "knowledge_used")
