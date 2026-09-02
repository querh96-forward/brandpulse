import asyncio
import logging

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.feed_source import FeedSource
from app.services.analysis_queue import dispatch_queued_analysis_jobs
from app.services.feed_source import collect_feed_source, is_feed_source_due

logger = logging.getLogger(__name__)


async def collect_due_feed_sources(
    redis_client: Redis,
    http_client: AsyncClient,
) -> int:
    processed_count = 0

    async with async_session_factory() as session:
        await dispatch_queued_analysis_jobs(
            session=session,
            redis_client=redis_client,
        )

        result = await session.scalars(
            select(FeedSource)
            .where(FeedSource.enabled.is_(True))
            .order_by(FeedSource.last_fetched_at.asc().nullsfirst())
        )
        sources = list(result.all())

        for source in sources:
            if not is_feed_source_due(source):
                continue

            try:
                collection = await collect_feed_source(
                    session=session,
                    redis_client=redis_client,
                    http_client=http_client,
                    source=source,
                )
            except Exception:
                logger.exception(
                    "RSS collection failed feed_source_id=%s feed_url=%s",
                    source.id,
                    source.feed_url,
                )
                continue

            processed_count += 1
            logger.info(
                "RSS collection completed feed_source_id=%s discovered=%s "
                "considered=%s truncated=%s imported=%s skipped=%s enqueued=%s",
                source.id,
                collection.discovered_count,
                collection.considered_count,
                collection.truncated_count,
                collection.imported_count,
                collection.skipped_count,
                collection.enqueued_count,
            )

    return processed_count


async def run_collector() -> None:
    settings = get_settings()
    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    logger.info(
        "RSS collector started poll_seconds=%s",
        settings.collector_poll_seconds,
    )

    try:
        async with AsyncClient(timeout=settings.rss_request_timeout_seconds) as http_client:
            while True:
                try:
                    await collect_due_feed_sources(
                        redis_client=redis_client,
                        http_client=http_client,
                    )
                except Exception:
                    logger.exception("RSS collector iteration failed")

                await asyncio.sleep(settings.collector_poll_seconds)
    finally:
        await redis_client.aclose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        asyncio.run(run_collector())
    except KeyboardInterrupt:
        logger.info("RSS collector stopped")


if __name__ == "__main__":
    main()
