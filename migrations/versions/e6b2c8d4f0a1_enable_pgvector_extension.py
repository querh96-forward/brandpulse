"""enable pgvector extension

Revision ID: e6b2c8d4f0a1
Revises: d5a1b7c3e9f2
Create Date: 2026-09-04 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6b2c8d4f0a1"
down_revision: str | Sequence[str] | None = "d5a1b7c3e9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable PostgreSQL's vector data type and similarity operators."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Disable pgvector when no vector-backed tables depend on it."""
    op.execute("DROP EXTENSION IF EXISTS vector")
