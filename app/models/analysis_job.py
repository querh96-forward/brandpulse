import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AnalysisJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(TimestampMixin, Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        Index(
            "uq_analysis_jobs_active_article_id",
            "article_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'processing')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=AnalysisJobStatus.QUEUED,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        default=None,
    )
