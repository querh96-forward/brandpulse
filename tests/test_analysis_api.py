import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob, AnalysisJobStatus


async def test_analyze_article_endpoint(client: AsyncClient) -> None:
    article_response = await client.post(
        "/api/v1/articles",
        json={
            "source_type": "manual",
            "source_name": "Test Source",
            "title": "水下设备出现故障",
            "content": "用户投诉设备在水下运行时发生进水故障。",
        },
    )

    assert article_response.status_code == 201
    article_id = article_response.json()["id"]

    first_response = await client.post(
        f"/api/v1/articles/{article_id}/analyze",
    )
    second_response = await client.post(
        f"/api/v1/articles/{article_id}/analyze",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_analysis = first_response.json()
    second_analysis = second_response.json()

    assert first_analysis["article_id"] == article_id
    assert first_analysis["model_name"] == "rule-based-v1"
    assert first_analysis["sentiment"] == "negative"
    assert first_analysis["risk_level"] == "high"
    assert first_analysis["risk_score"] == 0.85

    assert second_analysis["id"] == first_analysis["id"]


async def test_get_article_analysis(client: AsyncClient) -> None:
    article_response = await client.post(
        "/api/v1/articles",
        json={
            "source_type": "manual",
            "source_name": "Analysis Query Test",
            "title": "查询分析结果测试",
            "content": "用户投诉设备出现严重进水故障，需要立即处理。",
        },
    )

    assert article_response.status_code == 201
    article_id = article_response.json()["id"]

    pending_response = await client.get(
        f"/api/v1/articles/{article_id}/analysis",
    )

    assert pending_response.status_code == 404
    assert pending_response.json() == {
        "detail": "analysis result not found",
    }

    analyze_response = await client.post(
        f"/api/v1/articles/{article_id}/analyze",
    )

    assert analyze_response.status_code == 200

    result_response = await client.get(
        f"/api/v1/articles/{article_id}/analysis",
    )

    assert result_response.status_code == 200
    assert result_response.json()["id"] == analyze_response.json()["id"]
    assert result_response.json()["article_id"] == article_id


async def test_get_article_analysis_status(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    article_response = await client.post(
        "/api/v1/articles",
        json={
            "source_type": "manual",
            "source_name": "Status Test",
            "title": "异步状态查询测试",
            "content": "用户反馈设备发生进水故障，存在较高风险。",
        },
    )

    assert article_response.status_code == 201
    article_id = article_response.json()["id"]

    pending_response = await client.get(
        f"/api/v1/articles/{article_id}/analysis/status",
    )

    assert pending_response.status_code == 200
    assert pending_response.json() == {
        "article_id": article_id,
        "status": "not_submitted",
        "job_id": None,
        "attempts": 0,
        "last_error": None,
        "result": None,
    }

    job = AnalysisJob(
        article_id=uuid.UUID(article_id),
        status=AnalysisJobStatus.PROCESSING,
        attempts=1,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    processing_response = await client.get(
        f"/api/v1/articles/{article_id}/analysis/status",
    )

    assert processing_response.status_code == 200
    assert processing_response.json() == {
        "article_id": article_id,
        "status": "processing",
        "job_id": str(job.id),
        "attempts": 1,
        "last_error": None,
        "result": None,
    }

    analyze_response = await client.post(
        f"/api/v1/articles/{article_id}/analyze",
    )

    assert analyze_response.status_code == 200

    completed_response = await client.get(
        f"/api/v1/articles/{article_id}/analysis/status",
    )

    assert completed_response.status_code == 200

    data = completed_response.json()
    assert data["article_id"] == article_id
    assert data["status"] == "completed"
    assert data["result"]["article_id"] == article_id
