import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob, AnalysisJobStatus


async def test_database_rejects_two_active_jobs_for_same_article(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    article_response = await client.post(
        "/api/v1/articles",
        json={
            "source_type": "manual",
            "source_name": "Constraint Test",
            "title": "活动任务唯一约束测试",
            "content": "同一篇文章不能同时存在两个活动分析任务。",
        },
    )

    assert article_response.status_code == 201

    article_id = uuid.UUID(article_response.json()["id"])
    first_job = AnalysisJob(
        article_id=article_id,
        status=AnalysisJobStatus.QUEUED,
    )
    duplicate_job = AnalysisJob(
        article_id=article_id,
        status=AnalysisJobStatus.PROCESSING,
    )

    db_session.add(first_job)
    await db_session.flush()

    db_session.add(duplicate_job)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()
