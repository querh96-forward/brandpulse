import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class FeedSourceCreate(BaseModel):
    brand_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100)
    feed_url: HttpUrl
    enabled: bool = True
    interval_minutes: int = Field(default=15, ge=1, le=1440)
    max_articles_per_collection: int = Field(default=5, ge=1, le=50)


class FeedSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    feed_url: HttpUrl | None = None
    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    max_articles_per_collection: int | None = Field(default=None, ge=1, le=50)


class FeedSourceRead(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    name: str
    feed_url: str
    enabled: bool
    interval_minutes: int
    max_articles_per_collection: int
    last_fetched_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedCollectionRead(BaseModel):
    feed_source_id: uuid.UUID
    discovered_count: int
    considered_count: int
    truncated_count: int
    imported_count: int
    skipped_count: int
    enqueued_count: int
    collected_at: datetime
