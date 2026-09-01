import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob, AnalysisJobStatus


async def test_get_analysis_job_status(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    article_response = await client.post(
        "/api/v1/articles",
        json={
            "source_type": "manual",
            "source_name": "Job Status Test",
            "title": "任务状态查询测试",
            "content": "这是一篇用于测试异步任务状态接口的文章。",
        },
    )

    assert article_response.status_code == 201
    article_id = article_response.json()["id"]

    job = AnalysisJob(
        article_id=uuid.UUID(article_id),
        status=AnalysisJobStatus.PROCESSING,
        attempts=2,
        last_error="temporary error",
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    response = await client.get(
        f"/api/v1/analysis-jobs/{job.id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["job_id"] == str(job.id)
    assert data["article_id"] == article_id
    assert data["status"] == "processing"
    assert data["attempts"] == 2
    assert data["last_error"] == "temporary error"

    not_found_response = await client.get(
        f"/api/v1/analysis-jobs/{uuid.uuid4()}",
    )

    assert not_found_response.status_code == 404
    assert not_found_response.json() == {
        "detail": "analysis job not found",
    }
