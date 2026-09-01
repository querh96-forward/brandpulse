from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import AnalysisResult
    from app.models.brand import Brand


class Article(TimestampMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_articles_content_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"),
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2000))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    brand: Mapped[Brand | None] = relationship(back_populates="articles")
    analysis: Mapped[AnalysisResult | None] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        uselist=False,
    )
