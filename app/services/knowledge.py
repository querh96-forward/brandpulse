import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import KNOWLEDGE_EMBEDDING_DIMENSIONS, KnowledgeChunk
from app.providers.base import EmbeddingProvider, EvidenceProvider
from app.schemas.knowledge import EvidenceAssessment


@dataclass(frozen=True, slots=True)
class MarkdownSection:
    title: str
    content: str


@dataclass(frozen=True, slots=True)
class KnowledgeSearchResult:
    chunk_id: uuid.UUID
    source_name: str
    section_title: str | None
    content: str
    similarity: float


@dataclass(frozen=True, slots=True)
class AssessedKnowledge:
    results: list[KnowledgeSearchResult]
    assessment: EvidenceAssessment


def split_markdown_sections(markdown: str) -> list[MarkdownSection]:
    normalized_markdown = markdown.strip()

    if not normalized_markdown:
        raise ValueError("knowledge document must not be blank")

    document_title = "Untitled knowledge document"
    current_title: str | None = None
    current_lines: list[str] = []
    raw_sections: list[tuple[str, str]] = []

    for line in normalized_markdown.splitlines():
        if line.startswith("# ") and document_title == "Untitled knowledge document":
            document_title = line.removeprefix("# ").strip()
            continue

        if line.startswith("## "):
            if current_title is not None:
                raw_sections.append((current_title, "\n".join(current_lines).strip()))

            current_title = line.removeprefix("## ").strip()
            current_lines = []
            continue

        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        raw_sections.append((current_title, "\n".join(current_lines).strip()))

    if not raw_sections:
        return [MarkdownSection(title=document_title, content=normalized_markdown)]

    sections: list[MarkdownSection] = []

    for section_title, section_body in raw_sections:
        if not section_body:
            continue

        content = f"# {document_title}\n\n## {section_title}\n\n{section_body}"
        sections.append(MarkdownSection(title=section_title, content=content))

    if not sections:
        raise ValueError("knowledge document does not contain any non-empty sections")

    return sections


async def replace_markdown_knowledge(
    session: AsyncSession,
    provider: EmbeddingProvider,
    brand_id: uuid.UUID,
    source_name: str,
    markdown: str,
) -> list[KnowledgeChunk]:
    sections = split_markdown_sections(markdown)
    vectors = await provider.embed_texts([section.content for section in sections])

    chunks = [
        KnowledgeChunk(
            brand_id=brand_id,
            source_name=source_name,
            section_title=section.title,
            chunk_index=index,
            content=section.content,
            content_hash=hashlib.sha256(section.content.encode("utf-8")).hexdigest(),
            embedding_model=provider.model_name,
            embedding=vector,
        )
        for index, (section, vector) in enumerate(zip(sections, vectors, strict=True))
    ]

    await session.execute(
        delete(KnowledgeChunk).where(
            KnowledgeChunk.brand_id == brand_id,
            KnowledgeChunk.source_name == source_name,
        )
    )
    session.add_all(chunks)
    await session.flush()

    return chunks


async def search_knowledge(
    session: AsyncSession,
    provider: EmbeddingProvider,
    brand_id: uuid.UUID,
    query: str,
    limit: int = 3,
    similarity_threshold: float = 0.0,
) -> list[KnowledgeSearchResult]:
    query_vector = await provider.embed_text(query)

    return await search_knowledge_by_vector(
        session=session,
        brand_id=brand_id,
        query_vector=query_vector,
        limit=limit,
        similarity_threshold=similarity_threshold,
    )


async def search_knowledge_by_vector(
    session: AsyncSession,
    brand_id: uuid.UUID,
    query_vector: list[float],
    limit: int = 3,
    similarity_threshold: float = 0.0,
) -> list[KnowledgeSearchResult]:
    if not 1 <= limit <= 20:
        raise ValueError("knowledge search limit must be between 1 and 20")

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity threshold must be between 0 and 1")

    if len(query_vector) != KNOWLEDGE_EMBEDDING_DIMENSIONS:
        raise ValueError(
            "query embedding has an unexpected dimension: "
            f"expected {KNOWLEDGE_EMBEDDING_DIMENSIONS}, received {len(query_vector)}"
        )

    cosine_distance = KnowledgeChunk.embedding.cosine_distance(query_vector)

    rows = await session.execute(
        select(KnowledgeChunk, cosine_distance.label("cosine_distance"))
        .where(
            KnowledgeChunk.brand_id == brand_id,
            cosine_distance <= 1.0 - similarity_threshold,
        )
        .order_by(cosine_distance)
        .limit(limit)
    )

    return [
        KnowledgeSearchResult(
            chunk_id=chunk.id,
            source_name=chunk.source_name,
            section_title=chunk.section_title,
            content=chunk.content,
            similarity=max(-1.0, min(1.0, 1.0 - float(distance))),
        )
        for chunk, distance in rows.all()
    ]


async def retrieve_and_assess_knowledge(
    session: AsyncSession,
    embedding_provider: EmbeddingProvider,
    evidence_provider: EvidenceProvider,
    brand_id: uuid.UUID,
    query: str,
    limit: int = 3,
    similarity_threshold: float = 0.0,
) -> AssessedKnowledge:
    results = await search_knowledge(
        session=session,
        provider=embedding_provider,
        brand_id=brand_id,
        query=query,
        limit=limit,
        similarity_threshold=similarity_threshold,
    )

    if not results:
        return AssessedKnowledge(
            results=[],
            assessment=EvidenceAssessment(
                sufficient=False,
                supporting_ranks=[],
                reason="没有检索到候选证据。",
            ),
        )

    assessment = await evidence_provider.assess(
        query=query,
        evidence=[result.content for result in results],
    )

    return AssessedKnowledge(results=results, assessment=assessment)
