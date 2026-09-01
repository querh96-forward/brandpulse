import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.main import app
from app.models.analysis_job import AnalysisJob
from app.services.analysis_queue import ANALYSIS_QUEUE_KEY


async def test_enqueue_analysis_job(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    redis_client = AsyncMock()
    redis_client.rpush.return_value = 1

    async def override_get_redis_client() -> AsyncMock:
        return redis_client

    app.dependency_overrides[get_redis_client] = override_get_redis_client

    try:
        article_response = await client.post(
            "/api/v1/articles",
            json={
                "source_type": "manual",
                "source_name": "Queue Test",
                "title": "异步分析测试",
                "content": "这是一篇用于测试异步分析队列的文章。",
            },
        )

        assert article_response.status_code == 201
        article_id = article_response.json()["id"]

        response = await client.post(
            f"/api/v1/articles/{article_id}/analyze/async",
        )

        assert response.status_code == 202

        data = response.json()

        assert data["article_id"] == article_id
        assert data["status"] == "queued"
        assert data["queue_length"] == 1
        assert data["reused"] is False

        job_id = data["job_id"]

        duplicate_response = await client.post(
            f"/api/v1/articles/{article_id}/analyze/async",
        )

        assert duplicate_response.status_code == 202

        duplicate_data = duplicate_response.json()

        assert duplicate_data["job_id"] == job_id
        assert duplicate_data["article_id"] == article_id
        assert duplicate_data["status"] == "queued"
        assert duplicate_data["queue_length"] is None
        assert duplicate_data["reused"] is True

        redis_client.rpush.assert_awaited_once_with(
            ANALYSIS_QUEUE_KEY,
            job_id,
        )

        job = await db_session.get(
            AnalysisJob,
            uuid.UUID(job_id),
        )

        assert job is not None
        assert str(job.article_id) == article_id
        assert job.status == "queued"
        assert job.attempts == 0
        assert job.last_error is None
    finally:
        app.dependency_overrides.pop(get_redis_client, None)
