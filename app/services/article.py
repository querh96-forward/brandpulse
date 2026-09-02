import hashlib
import uuid

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
    imported_articles, skipped_count = await stage_collected_articles(
        session=session,
        articles=articles,
    )

    await session.commit()

    return len(imported_articles), skipped_count


async def stage_collected_articles(
    session: AsyncSession,
    articles: list[ArticleCreate],
    feed_source_id: uuid.UUID | None = None,
) -> tuple[list[Article], int]:
    imported_articles: list[Article] = []
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

        article = Article(
            brand_id=payload.brand_id,
            feed_source_id=feed_source_id,
            source_type=payload.source_type,
            source_name=payload.source_name,
            title=payload.title,
            content=payload.content,
            url=payload.url,
            content_hash=content_hash,
            published_at=payload.published_at,
        )
        session.add(article)
        imported_articles.append(article)

    await session.flush()

    return imported_articles, skipped_count
