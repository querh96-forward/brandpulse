import asyncio
import logging
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.article import Article
from app.providers.base import AnalysisProvider
from app.providers.dependencies import get_analysis_provider
from app.services.analysis import analyze_and_save_article
from app.services.analysis_queue import (
    acknowledge_analysis_job,
    claim_next_analysis_job,
    recover_processing_jobs,
    requeue_analysis_job,
)

logger = logging.getLogger(__name__)
MAX_ANALYSIS_ATTEMPTS = 3


async def process_next_analysis_job(
    redis_client: Redis,
    session: AsyncSession,
    provider: AnalysisProvider,
) -> bool:
    raw_job_id = await claim_next_analysis_job(redis_client)

    if raw_job_id is None:
        return False

    try:
        job_id = uuid.UUID(raw_job_id)
    except ValueError:
        logger.warning(
            "discarding invalid analysis job id raw_job_id=%r",
            raw_job_id,
        )
        await acknowledge_analysis_job(
            redis_client,
            raw_job_id,
        )
        return False

    job = await session.get(AnalysisJob, job_id)

    if job is None:
        logger.warning(
            "discarding missing analysis job job_id=%s",
            job_id,
        )
        await acknowledge_analysis_job(
            redis_client,
            raw_job_id,
        )
        return False

    if job.status == AnalysisJobStatus.COMPLETED:
        await acknowledge_analysis_job(
            redis_client,
            raw_job_id,
        )
        return True

    if job.status == AnalysisJobStatus.FAILED:
        await acknowledge_analysis_job(
            redis_client,
            raw_job_id,
        )
        return False

    article = await session.get(Article, job.article_id)

    if article is None:
        job.status = AnalysisJobStatus.FAILED
        job.last_error = "article not found"
        await session.commit()

        logger.error(
            "analysis job failed job_id=%s article_id=%s reason=article_not_found",
            job.id,
            job.article_id,
        )

        await acknowledge_analysis_job(
            redis_client,
            raw_job_id,
        )
        return False

    job.status = AnalysisJobStatus.PROCESSING
    job.attempts += 1
    job.last_error = None
    await session.commit()

    logger.info(
        "analysis job started job_id=%s article_id=%s attempt=%s provider=%s",
        job.id,
        article.id,
        job.attempts,
        provider.model_name,
    )

    try:
        await analyze_and_save_article(
            session=session,
            provider=provider,
            article=article,
        )
    except Exception as exc:
        await session.rollback()

        job = await session.get(AnalysisJob, job_id)
        should_retry = False

        if job is not None:
            job.last_error = str(exc)

            if job.attempts >= MAX_ANALYSIS_ATTEMPTS:
                job.status = AnalysisJobStatus.FAILED
            else:
                job.status = AnalysisJobStatus.QUEUED
                should_retry = True

            await session.commit()

            log_method = logger.warning if should_retry else logger.error
            log_method(
                "analysis job attempt failed job_id=%s article_id=%s "
                "attempt=%s max_attempts=%s next_status=%s error=%s",
                job.id,
                job.article_id,
                job.attempts,
                MAX_ANALYSIS_ATTEMPTS,
                job.status,
                exc,
            )

        if should_retry:
            await requeue_analysis_job(
                redis_client,
                raw_job_id,
            )
        else:
            await acknowledge_analysis_job(
                redis_client,
                raw_job_id,
            )

        raise

    job = await session.get(AnalysisJob, job_id)

    if job is not None:
        job.status = AnalysisJobStatus.COMPLETED
        job.last_error = None
        await session.commit()

        logger.info(
            "analysis job completed job_id=%s article_id=%s attempt=%s provider=%s",
            job.id,
            job.article_id,
            job.attempts,
            provider.model_name,
        )

    await acknowledge_analysis_job(
        redis_client,
        raw_job_id,
    )

    return True


async def run_analysis_worker() -> None:
    settings = get_settings()

    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    provider = get_analysis_provider()

    try:
        recovered_count = await recover_processing_jobs(
            redis_client,
        )

        if recovered_count:
            logger.warning(
                "recovered %s interrupted analysis jobs",
                recovered_count,
            )

        logger.info(
            "analysis worker started with provider=%s",
            provider.model_name,
        )

        while True:
            async with async_session_factory() as session:
                try:
                    processed = await process_next_analysis_job(
                        redis_client=redis_client,
                        session=session,
                        provider=provider,
                    )
                except Exception:
                    logger.exception("analysis worker iteration failed; retrying in 5 seconds")
                    await asyncio.sleep(5)
                    continue

            if not processed:
                await asyncio.sleep(1)
    finally:
        await redis_client.aclose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        asyncio.run(run_analysis_worker())
    except KeyboardInterrupt:
        logger.info("analysis worker stopped")


if __name__ == "__main__":
    main()
