from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob
from app.models.feed_source import FeedSource
from app.services.analysis_queue import dispatch_queued_analysis_jobs
from app.services.article import stage_collected_articles
from app.services.rss import fetch_and_parse_rss_feed


@dataclass(frozen=True)
class FeedCollectionResult:
    discovered_count: int
    considered_count: int
    truncated_count: int
    imported_count: int
    skipped_count: int
    enqueued_count: int
    collected_at: datetime


def is_feed_source_due(
    source: FeedSource,
    now: datetime | None = None,
) -> bool:
    if not source.enabled:
        return False

    if source.last_fetched_at is None:
        return True

    current_time = now or datetime.now(UTC)
    return source.last_fetched_at <= current_time - timedelta(minutes=source.interval_minutes)


async def collect_feed_source(
    session: AsyncSession,
    redis_client: Redis,
    http_client: AsyncClient,
    source: FeedSource,
) -> FeedCollectionResult:
    collected_at = datetime.now(UTC)

    try:
        articles = await fetch_and_parse_rss_feed(
            client=http_client,
            url=source.feed_url,
            source_name=source.name,
            brand_id=source.brand_id,
        )
        considered_articles = articles[: source.max_articles_per_collection]
        imported_articles, skipped_count = await stage_collected_articles(
            session=session,
            articles=considered_articles,
            feed_source_id=source.id,
        )
        jobs = [AnalysisJob(article_id=article.id) for article in imported_articles]
        session.add_all(jobs)

        source.last_fetched_at = collected_at
        source.last_success_at = collected_at
        source.last_error = None
        await session.commit()

        await dispatch_queued_analysis_jobs(
            session=session,
            redis_client=redis_client,
        )
    except Exception as exc:
        await session.rollback()
        persisted_source = await session.get(FeedSource, source.id)

        if persisted_source is not None:
            persisted_source.last_fetched_at = collected_at
            persisted_source.last_error = str(exc)[:2000]
            await session.commit()

        raise

    return FeedCollectionResult(
        discovered_count=len(articles),
        considered_count=len(considered_articles),
        truncated_count=max(0, len(articles) - len(considered_articles)),
        imported_count=len(imported_articles),
        skipped_count=skipped_count,
        enqueued_count=len(jobs),
        collected_at=collected_at,
    )
