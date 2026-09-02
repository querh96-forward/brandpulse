from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.brand import Brand


class FeedSource(TimestampMixin, Base):
    __tablename__ = "feed_sources"
    __table_args__ = (
        CheckConstraint(
            "interval_minutes BETWEEN 1 AND 1440",
            name="ck_feed_sources_interval_minutes",
        ),
        CheckConstraint(
            "max_articles_per_collection BETWEEN 1 AND 50",
            name="ck_feed_sources_max_articles_per_collection",
        ),
        UniqueConstraint(
            "brand_id",
            "feed_url",
            name="uq_feed_sources_brand_id_feed_url",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    feed_url: Mapped[str] = mapped_column(String(2000))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    max_articles_per_collection: Mapped[int] = mapped_column(Integer, default=5)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    brand: Mapped[Brand] = relationship(back_populates="feed_sources")
    articles: Mapped[list[Article]] = relationship(back_populates="feed_source")
