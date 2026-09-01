import uuid
from unittest.mock import AsyncMock

from app.services.analysis_queue import (
    ANALYSIS_PROCESSING_QUEUE_KEY,
    ANALYSIS_QUEUE_KEY,
    acknowledge_analysis_job,
    claim_next_analysis_job,
    enqueue_analysis_job,
    recover_processing_jobs,
    requeue_analysis_job,
)


async def test_enqueue_analysis_job() -> None:
    redis_client = AsyncMock()
    redis_client.rpush.return_value = 1

    job_id = uuid.uuid4()

    queue_length = await enqueue_analysis_job(
        redis_client=redis_client,
        job_id=job_id,
    )

    assert queue_length == 1
    redis_client.rpush.assert_awaited_once_with(
        ANALYSIS_QUEUE_KEY,
        str(job_id),
    )


async def test_claim_next_analysis_job() -> None:
    redis_client = AsyncMock()
    job_id = str(uuid.uuid4())
    redis_client.lmove.return_value = job_id

    claimed_job_id = await claim_next_analysis_job(redis_client)

    assert claimed_job_id == job_id
    redis_client.lmove.assert_awaited_once_with(
        ANALYSIS_QUEUE_KEY,
        ANALYSIS_PROCESSING_QUEUE_KEY,
        "LEFT",
        "RIGHT",
    )


async def test_acknowledge_analysis_job() -> None:
    redis_client = AsyncMock()
    redis_client.lrem.return_value = 1
    job_id = str(uuid.uuid4())

    acknowledged = await acknowledge_analysis_job(
        redis_client,
        job_id,
    )

    assert acknowledged is True
    redis_client.lrem.assert_awaited_once_with(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        1,
        job_id,
    )


async def test_requeue_analysis_job() -> None:
    redis_client = AsyncMock()
    redis_client.lpush.return_value = 2
    redis_client.lrem.return_value = 1
    job_id = str(uuid.uuid4())

    queue_length = await requeue_analysis_job(
        redis_client,
        job_id,
    )

    assert queue_length == 2

    redis_client.lpush.assert_awaited_once_with(
        ANALYSIS_QUEUE_KEY,
        job_id,
    )
    redis_client.lrem.assert_awaited_once_with(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        1,
        job_id,
    )


async def test_recover_processing_jobs() -> None:
    redis_client = AsyncMock()
    redis_client.lmove.side_effect = [
        "job-1",
        "job-2",
        None,
    ]

    recovered_count = await recover_processing_jobs(redis_client)

    assert recovered_count == 2
    assert redis_client.lmove.await_count == 3
    redis_client.lmove.assert_awaited_with(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        ANALYSIS_QUEUE_KEY,
        "RIGHT",
        "LEFT",
    )
