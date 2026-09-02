import uuid

from httpx import AsyncClient
from pytest import MonkeyPatch

from app.schemas.article import ArticleCreate


async def test_import_rss_articles(
    client: AsyncClient,
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_fetch_and_parse_rss_feed(
        client: AsyncClient,
        url: str,
        source_name: str,
        brand_id: uuid.UUID | None = None,
    ) -> list[ArticleCreate]:
        return [
            ArticleCreate(
                brand_id=brand_id,
                source_type="rss",
                source_name=source_name,
                title="RSS 自动采集文章",
                content="这篇文章由假的 RSS 网站返回。",
                url="https://example.com/articles/1",
            )
        ]

    monkeypatch.setattr(
        "app.api.routes.articles.fetch_and_parse_rss_feed",
        fake_fetch_and_parse_rss_feed,
    )

    brand_response = await client.post(
        "/api/v1/brands",
        json={
            "name": "RssImportBrand",
            "description": "用于测试 RSS 导入",
        },
    )
    brand_id = brand_response.json()["id"]

    payload = {
        "brand_id": brand_id,
        "feed_url": "https://example.com/rss.xml",
        "source_name": "Test RSS Feed",
    }

    first_response = await client.post(
        "/api/v1/articles/import/rss",
        json=payload,
    )
    second_response = await client.post(
        "/api/v1/articles/import/rss",
        json=payload,
    )

    assert first_response.status_code == 200
    assert first_response.json() == {
        "discovered_count": 1,
        "considered_count": 1,
        "truncated_count": 0,
        "imported_count": 1,
        "skipped_count": 0,
    }

    assert second_response.status_code == 200
    assert second_response.json() == {
        "discovered_count": 1,
        "considered_count": 1,
        "truncated_count": 0,
        "imported_count": 0,
        "skipped_count": 1,
    }
