import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

KNOWLEDGE_EMBEDDING_DIMENSIONS = 1024


class KnowledgeChunk(TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_chunk_index"),
        UniqueConstraint(
            "brand_id",
            "content_hash",
            name="uq_knowledge_chunks_brand_content_hash",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"),
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    section_title: Mapped[str | None] = mapped_column(String(500))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(100))
    embedding: Mapped[list[float]] = mapped_column(Vector(KNOWLEDGE_EMBEDDING_DIMENSIONS))
