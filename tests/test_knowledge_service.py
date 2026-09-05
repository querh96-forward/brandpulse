import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import Brand
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.knowledge import (
    replace_markdown_knowledge,
    search_knowledge,
    split_markdown_sections,
)


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"
    dimensions = 1024

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index + 1)] * self.dimensions for index, _ in enumerate(texts)]


class FixedQueryEmbeddingProvider(FakeEmbeddingProvider):
    async def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        vector[0] = 1.0
        return vector


def test_split_markdown_sections_adds_document_context() -> None:
    sections = split_markdown_sections(
        """# BlueCurrent 手册

> 文档元数据

## 产品信息

BC-D200 的工作深度为 200 米。

## 响应时限

P0 事件应在 4 小时内发布首次说明。
"""
    )

    assert [section.title for section in sections] == ["产品信息", "响应时限"]
    assert sections[0].content.startswith("# BlueCurrent 手册\n\n## 产品信息")
    assert "200 米" in sections[0].content
    assert "4 小时" not in sections[0].content
    assert "4 小时" in sections[1].content


async def test_replace_markdown_knowledge_replaces_stale_source_chunks(
    db_session: AsyncSession,
) -> None:
    brand = Brand(name=f"Knowledge Brand {uuid.uuid4()}", description=None)
    db_session.add(brand)
    await db_session.flush()

    provider = FakeEmbeddingProvider()
    source_name = "policy.md"

    first_chunks = await replace_markdown_knowledge(
        session=db_session,
        provider=provider,
        brand_id=brand.id,
        source_name=source_name,
        markdown="# Policy\n\n## One\n\nFirst.\n\n## Two\n\nSecond.",
    )
    assert len(first_chunks) == 2

    second_chunks = await replace_markdown_knowledge(
        session=db_session,
        provider=provider,
        brand_id=brand.id,
        source_name=source_name,
        markdown="# Policy\n\n## Updated\n\nOnly the current policy remains.",
    )
    assert len(second_chunks) == 1

    stored_chunks = list(
        await db_session.scalars(
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.brand_id == brand.id,
                KnowledgeChunk.source_name == source_name,
            )
            .order_by(KnowledgeChunk.chunk_index)
        )
    )

    assert len(stored_chunks) == 1
    assert stored_chunks[0].section_title == "Updated"
    assert stored_chunks[0].embedding_model == provider.model_name
    assert len(stored_chunks[0].embedding) == provider.dimensions


async def test_search_knowledge_orders_by_cosine_similarity(
    db_session: AsyncSession,
) -> None:
    brand = Brand(name=f"Search Brand {uuid.uuid4()}", description=None)
    other_brand = Brand(name=f"Other Brand {uuid.uuid4()}", description=None)
    db_session.add_all([brand, other_brand])
    await db_session.flush()

    matching_vector = [0.0] * 1024
    matching_vector[0] = 1.0
    orthogonal_vector = [0.0] * 1024
    orthogonal_vector[1] = 1.0

    db_session.add_all(
        [
            KnowledgeChunk(
                brand_id=brand.id,
                source_name="policy.md",
                section_title="Matching",
                chunk_index=0,
                content="Matching knowledge",
                content_hash="a" * 64,
                embedding_model="fake-embedding-model",
                embedding=matching_vector,
            ),
            KnowledgeChunk(
                brand_id=brand.id,
                source_name="policy.md",
                section_title="Orthogonal",
                chunk_index=1,
                content="Orthogonal knowledge",
                content_hash="b" * 64,
                embedding_model="fake-embedding-model",
                embedding=orthogonal_vector,
            ),
            KnowledgeChunk(
                brand_id=other_brand.id,
                source_name="private.md",
                section_title="Other brand",
                chunk_index=0,
                content="Other brand knowledge",
                content_hash="c" * 64,
                embedding_model="fake-embedding-model",
                embedding=matching_vector,
            ),
        ]
    )
    await db_session.flush()

    results = await search_knowledge(
        session=db_session,
        provider=FixedQueryEmbeddingProvider(),
        brand_id=brand.id,
        query="matching query",
        limit=3,
    )

    assert [result.section_title for result in results] == ["Matching", "Orthogonal"]
    assert results[0].similarity == 1.0
    assert results[1].similarity == 0.0
    assert all(result.source_name != "private.md" for result in results)
