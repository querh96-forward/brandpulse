from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisResult
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.article import Article
from app.schemas.analysis import AnalysisOutput
from app.services.analysis_queue import (
    ANALYSIS_PROCESSING_QUEUE_KEY,
    ANALYSIS_QUEUE_KEY,
)
from app.services.article import calculate_content_hash
from app.workers.analysis import process_next_analysis_job


class FakeAnalysisProvider:
    model_name = "fake-worker-model"

    async def analyze(self, prompt: str) -> AnalysisOutput:
        return AnalysisOutput(
            sentiment="negative",
            sentiment_score=-0.7,
            risk_level="high",
            risk_score=0.8,
            risk_type="product_risk",
            summary="Worker 检测到产品风险。",
            suggestion="建议及时核查并回应。",
        )


class FailingAnalysisProvider:
    model_name = "failing-provider"

    async def analyze(self, prompt: str) -> AnalysisOutput:
        raise RuntimeError("simulated provider failure")


async def test_process_next_analysis_job(
    db_session: AsyncSession,
) -> None:
    content = "用户反馈水下设备出现进水故障。"

    article = Article(
        source_type="manual",
        source_name="Worker Test",
        title="水下设备故障",
        content=content,
        content_hash=calculate_content_hash(content),
    )

    db_session.add(article)
    await db_session.flush()

    job = AnalysisJob(article_id=article.id)
    db_session.add(job)
    await db_session.flush()

    redis_client = AsyncMock()
    redis_client.lmove.return_value = str(job.id)
    redis_client.lrem.return_value = 1

    processed = await process_next_analysis_job(
        redis_client=redis_client,
        session=db_session,
        provider=FakeAnalysisProvider(),
    )

    assert processed is True
    redis_client.lmove.assert_awaited_once_with(
        ANALYSIS_QUEUE_KEY,
        ANALYSIS_PROCESSING_QUEUE_KEY,
        "LEFT",
        "RIGHT",
    )

    redis_client.lrem.assert_awaited_once_with(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        1,
        str(job.id),
    )

    analysis = await db_session.scalar(
        select(AnalysisResult).where(
            AnalysisResult.article_id == article.id,
        )
    )

    assert analysis is not None
    assert analysis.model_name == "fake-worker-model"
    assert analysis.risk_level == "high"
    await db_session.refresh(job)

    assert job.status == AnalysisJobStatus.COMPLETED
    assert job.attempts == 1
    assert job.last_error is None


async def test_process_next_analysis_job_returns_false_when_queue_empty(
    db_session: AsyncSession,
) -> None:
    redis_client = AsyncMock()
    redis_client.lmove.return_value = None

    processed = await process_next_analysis_job(
        redis_client=redis_client,
        session=db_session,
        provider=FakeAnalysisProvider(),
    )

    assert processed is False

    redis_client.lmove.assert_awaited_once_with(
        ANALYSIS_QUEUE_KEY,
        ANALYSIS_PROCESSING_QUEUE_KEY,
        "LEFT",
        "RIGHT",
    )


async def test_failed_analysis_job_is_requeued(
    db_session: AsyncSession,
) -> None:
    content = "用于测试任务重新入队的文章。"

    article = Article(
        source_type="manual",
        source_name="Retry Test",
        title="任务重试测试",
        content=content,
        content_hash=calculate_content_hash(content),
    )

    db_session.add(article)
    await db_session.flush()

    job = AnalysisJob(article_id=article.id)
    db_session.add(job)
    await db_session.flush()

    redis_client = AsyncMock()
    redis_client.lmove.return_value = str(job.id)
    redis_client.lpush.return_value = 1
    redis_client.lrem.return_value = 1

    with pytest.raises(
        RuntimeError,
        match="simulated provider failure",
    ):
        await process_next_analysis_job(
            redis_client=redis_client,
            session=db_session,
            provider=FailingAnalysisProvider(),
        )

    await db_session.refresh(job)

    assert job.status == AnalysisJobStatus.QUEUED
    assert job.attempts == 1
    assert job.last_error == "simulated provider failure"

    redis_client.lpush.assert_awaited_once_with(
        ANALYSIS_QUEUE_KEY,
        str(job.id),
    )
    redis_client.lrem.assert_awaited_once_with(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        1,
        str(job.id),
    )


async def test_analysis_job_stops_after_max_attempts(
    db_session: AsyncSession,
) -> None:
    content = "用于测试最大尝试次数的文章。"

    article = Article(
        source_type="manual",
        source_name="Max Attempts Test",
        title="最大尝试次数测试",
        content=content,
        content_hash=calculate_content_hash(content),
    )

    db_session.add(article)
    await db_session.flush()

    job = AnalysisJob(
        article_id=article.id,
        attempts=2,
    )
    db_session.add(job)
    await db_session.flush()

    redis_client = AsyncMock()
    redis_client.lmove.return_value = str(job.id)
    redis_client.lrem.return_value = 1

    with pytest.raises(
        RuntimeError,
        match="simulated provider failure",
    ):
        await process_next_analysis_job(
            redis_client=redis_client,
            session=db_session,
            provider=FailingAnalysisProvider(),
        )

    await db_session.refresh(job)

    assert job.status == AnalysisJobStatus.FAILED
    assert job.attempts == 3
    assert job.last_error == "simulated provider failure"

    redis_client.lpush.assert_not_awaited()
    redis_client.lrem.assert_awaited_once_with(
        ANALYSIS_PROCESSING_QUEUE_KEY,
        1,
        str(job.id),
    )
