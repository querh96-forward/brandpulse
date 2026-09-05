from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.article import Article


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisResult(TimestampMixin, Base):
    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    sentiment: Mapped[str] = mapped_column(String(20))
    sentiment_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20), index=True)
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    risk_type: Mapped[str] = mapped_column(String(100), index=True)
    summary: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(30), default="v1")
    knowledge_used: Mapped[bool] = mapped_column(Boolean, default=False)
    knowledge_citations: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        default=list,
    )
    retrieval_model_name: Mapped[str | None] = mapped_column(String(100))
    evidence_model_name: Mapped[str | None] = mapped_column(String(100))
    evidence_reason: Mapped[str | None] = mapped_column(Text)

    article: Mapped[Article] = relationship(back_populates="analysis")
