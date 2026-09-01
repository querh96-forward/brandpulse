import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.schemas.article import ArticleCreate


def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def save_collected_articles(
    session: AsyncSession,
    articles: list[ArticleCreate],
) -> tuple[int, int]:
    imported_count = 0
    skipped_count = 0

    for payload in articles:
        content_hash = calculate_content_hash(payload.content)

        existing_hash = await session.scalar(
            select(Article.content_hash).where(
                Article.content_hash == content_hash,
            )
        )

        if existing_hash is not None:
            skipped_count += 1
            continue

        session.add(
            Article(
                brand_id=payload.brand_id,
                source_type=payload.source_type,
                source_name=payload.source_name,
                title=payload.title,
                content=payload.content,
                url=payload.url,
                content_hash=content_hash,
                published_at=payload.published_at,
            )
        )
        imported_count += 1

    await session.commit()

    return imported_count, skipped_count
