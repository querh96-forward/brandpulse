import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ArticleCreate(BaseModel):
    brand_id: uuid.UUID | None = None
    source_type: str = Field(min_length=1, max_length=50)
    source_name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    url: str | None = Field(default=None, max_length=2000)
    published_at: datetime | None = None


class ArticleRead(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID | None
    feed_source_id: uuid.UUID | None
    source_type: str
    source_name: str
    title: str
    content: str
    url: str | None
    content_hash: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RssImportRequest(BaseModel):
    brand_id: uuid.UUID
    feed_url: HttpUrl
    source_name: str = Field(min_length=1, max_length=100)
    max_articles: int = Field(default=5, ge=1, le=50)


class RssImportRead(BaseModel):
    discovered_count: int
    considered_count: int
    truncated_count: int
    imported_count: int
    skipped_count: int
