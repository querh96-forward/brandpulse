import uuid

from redis.asyncio import Redis

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
