import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from httpx import AsyncClient, MockTransport, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import get_http_client
from app.core.redis import get_redis_client
from app.main import app
from app.models.analysis_job import AnalysisJob
from app.models.article import Article
from app.models.feed_source import FeedSource
from app.services.analysis_queue import ANALYSIS_QUEUE_KEY
from app.services.feed_source import is_feed_source_due


async def test_feed_source_crud_and_manual_collection(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    items = "".join(
        f"""
        <item>
          <title>自动采集到的文章 {index}</title>
          <link>https://example.com/articles/automatic-{index}</link>
          <description>第 {index} 篇产品反馈，正文内容各不相同。</description>
        </item>
        """
        for index in range(1, 8)
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Brand News</title>
        {items}
      </channel>
    </rss>
    """

    async def handle_request(request: Request) -> Response:
        assert str(request.url) == "https://example.com/brand.xml"
        return Response(
            200,
            text=xml,
            headers={"content-type": "application/rss+xml"},
        )

    http_client = AsyncClient(transport=MockTransport(handle_request))
    redis_client = AsyncMock()
    queued_job_ids: set[str] = set()

    async def fake_lpos(key: str, job_id: str) -> int | None:
        if key == ANALYSIS_QUEUE_KEY and job_id in queued_job_ids:
            return 0
        return None

    async def fake_rpush(key: str, job_id: str) -> int:
        assert key == ANALYSIS_QUEUE_KEY
        queued_job_ids.add(job_id)
        return len(queued_job_ids)

    redis_client.lpos.side_effect = fake_lpos
    redis_client.rpush.side_effect = fake_rpush

    async def override_get_http_client() -> AsyncClient:
        return http_client

    async def override_get_redis_client() -> AsyncMock:
        return redis_client

    app.dependency_overrides[get_http_client] = override_get_http_client
    app.dependency_overrides[get_redis_client] = override_get_redis_client

    try:
        brand_response = await client.post(
            "/api/v1/brands",
            json={
                "name": "AutomaticRssBrand",
                "description": "自动 RSS 采集测试品牌",
            },
        )
        brand_id = brand_response.json()["id"]

        create_response = await client.post(
            "/api/v1/feed-sources",
            json={
                "brand_id": brand_id,
                "name": "Brand News RSS",
                "feed_url": "https://example.com/brand.xml",
                "interval_minutes": 5,
                "max_articles_per_collection": 2,
            },
        )

        assert create_response.status_code == 201
        source_data = create_response.json()
        source_id = source_data["id"]
        assert source_data["enabled"] is True
        assert source_data["interval_minutes"] == 5
        assert source_data["max_articles_per_collection"] == 2
        assert source_data["last_fetched_at"] is None

        list_response = await client.get(f"/api/v1/feed-sources?brand_id={brand_id}")
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()] == [source_id]

        patch_response = await client.patch(
            f"/api/v1/feed-sources/{source_id}",
            json={"interval_minutes": 10},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["interval_minutes"] == 10

        first_collection = await client.post(f"/api/v1/feed-sources/{source_id}/collect")
        second_collection = await client.post(f"/api/v1/feed-sources/{source_id}/collect")

        assert first_collection.status_code == 200
        assert first_collection.json()["discovered_count"] == 7
        assert first_collection.json()["considered_count"] == 2
        assert first_collection.json()["truncated_count"] == 5
        assert first_collection.json()["imported_count"] == 2
        assert first_collection.json()["skipped_count"] == 0
        assert first_collection.json()["enqueued_count"] == 2

        assert second_collection.status_code == 200
        assert second_collection.json()["discovered_count"] == 7
        assert second_collection.json()["considered_count"] == 2
        assert second_collection.json()["truncated_count"] == 5
        assert second_collection.json()["imported_count"] == 0
        assert second_collection.json()["skipped_count"] == 2
        assert second_collection.json()["enqueued_count"] == 0

        source = await db_session.get(FeedSource, uuid.UUID(source_id))
        assert source is not None
        assert source.last_fetched_at is not None
        assert source.last_success_at is not None
        assert source.last_error is None

        articles = list(
            await db_session.scalars(select(Article).where(Article.feed_source_id == source.id))
        )
        assert len(articles) == 2
        assert all(article.source_type == "rss" for article in articles)

        jobs = list(
            await db_session.scalars(
                select(AnalysisJob).where(
                    AnalysisJob.article_id.in_([article.id for article in articles])
                )
            )
        )
        assert len(jobs) == 2
        assert all(job.status == "queued" for job in jobs)
        assert queued_job_ids == {str(job.id) for job in jobs}
    finally:
        app.dependency_overrides.pop(get_http_client, None)
        app.dependency_overrides.pop(get_redis_client, None)
        await http_client.aclose()


async def test_duplicate_feed_source_returns_conflict(client: AsyncClient) -> None:
    brand_response = await client.post(
        "/api/v1/brands",
        json={"name": "DuplicateFeedBrand", "description": None},
    )
    brand_id = brand_response.json()["id"]
    payload = {
        "brand_id": brand_id,
        "name": "Duplicate RSS",
        "feed_url": "https://example.com/duplicate.xml",
    }

    first_response = await client.post("/api/v1/feed-sources", json=payload)
    second_response = await client.post("/api/v1/feed-sources", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_feed_source_due_calculation() -> None:
    now = datetime.now(UTC)
    source = FeedSource(
        brand_id=uuid.uuid4(),
        name="Due Test",
        feed_url="https://example.com/due.xml",
        enabled=True,
        interval_minutes=15,
    )

    assert is_feed_source_due(source, now=now) is True

    source.last_fetched_at = now - timedelta(minutes=14)
    assert is_feed_source_due(source, now=now) is False

    source.last_fetched_at = now - timedelta(minutes=15)
    assert is_feed_source_due(source, now=now) is True

    source.enabled = False
    assert is_feed_source_due(source, now=now) is False
