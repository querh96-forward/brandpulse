import uuid

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob, AnalysisJobStatus

ANALYSIS_QUEUE_KEY = "brandpulse:analysis:jobs"
ANALYSIS_PROCESSING_QUEUE_KEY = "brandpulse:analysis:jobs:processing"


async def enqueue_analysis_job(
    redis_client: Redis,
    job_id: uuid.UUID,
) -> int:
    queue_length = await redis_client.rpush(
        ANALYSIS_QUEUE_KEY,
        str(job_id),
    )

    return int(queue_length)


async def enqueue_analysis_job_if_missing(
    redis_client: Redis,
    job_id: uuid.UUID,
) -> bool:
    raw_job_id = str(job_id)
    pending_position = await redis_client.lpos(
        ANALYSIS_QUEUE_KEY,
        raw_job_id,
    )
    processing_position = await redis_client.lpos(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        raw_job_id,
    )

    if pending_position is not None or processing_position is not None:
        return False

    await enqueue_analysis_job(redis_client, job_id)
    return True


async def dispatch_queued_analysis_jobs(
    session: AsyncSession,
    redis_client: Redis,
    limit: int = 100,
) -> int:
    result = await session.scalars(
        select(AnalysisJob)
        .where(AnalysisJob.status == AnalysisJobStatus.QUEUED)
        .order_by(AnalysisJob.created_at)
        .limit(limit)
    )
    dispatched_count = 0

    for job in result.all():
        if await enqueue_analysis_job_if_missing(redis_client, job.id):
            dispatched_count += 1

    return dispatched_count


async def claim_next_analysis_job(
    redis_client: Redis,
) -> str | None:
    return await redis_client.lmove(
        ANALYSIS_QUEUE_KEY,
        ANALYSIS_PROCESSING_QUEUE_KEY,
        "LEFT",
        "RIGHT",
    )


async def acknowledge_analysis_job(
    redis_client: Redis,
    job_id: str,
) -> bool:
    removed_count = await redis_client.lrem(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        1,
        job_id,
    )

    return bool(removed_count)


async def requeue_analysis_job(
    redis_client: Redis,
    job_id: str,
) -> int:
    queue_length = await redis_client.lpush(
        ANALYSIS_QUEUE_KEY,
        job_id,
    )

    await redis_client.lrem(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        1,
        job_id,
    )

    return int(queue_length)


async def recover_processing_jobs(
    redis_client: Redis,
) -> int:
    recovered_count = 0

    while True:
        job_id = await redis_client.lmove(
            ANALYSIS_PROCESSING_QUEUE_KEY,
            ANALYSIS_QUEUE_KEY,
            "RIGHT",
            "LEFT",
        )

        if job_id is None:
            return recovered_count

        recovered_count += 1
