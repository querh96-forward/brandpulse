import hashlib
import uuid

from httpx import AsyncClient


async def test_create_article(client: AsyncClient) -> None:
    brand_response = await client.post(
        "/api/v1/brands",
        json={
            "name": "ArticleTestBrand",
            "description": "用于测试文章接口",
        },
    )

    assert brand_response.status_code == 201

    brand_id = brand_response.json()["id"]
    content = "BlueCurrent发布了新一代水下视觉设备。"

    article_response = await client.post(
        "/api/v1/articles",
        json={
            "brand_id": brand_id,
            "source_type": "news",
            "source_name": "Ocean Technology Daily",
            "title": "水下智能设备发布新产品",
            "content": content,
            "url": "https://example.com/news/1",
            "published_at": "2026-08-08T10:00:00+08:00",
        },
    )

    assert article_response.status_code == 201

    article = article_response.json()
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    assert uuid.UUID(article["id"])
    assert article["brand_id"] == brand_id
    assert article["title"] == "水下智能设备发布新产品"
    assert article["content"] == content
    assert article["content_hash"] == expected_hash

    detail_response = await client.get(
        f"/api/v1/articles/{article['id']}",
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == article["id"]
    assert detail_response.json()["content_hash"] == expected_hash

    list_response = await client.get(
        "/api/v1/articles",
        params={
            "brand_id": brand_id,
            "offset": 0,
            "limit": 20,
        },
    )

    assert list_response.status_code == 200

    articles = list_response.json()
    assert len(articles) == 1
    assert articles[0]["id"] == article["id"]
    assert articles[0]["brand_id"] == brand_id


async def test_create_article_with_unknown_brand_returns_not_found(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/articles",
        json={
            "brand_id": "00000000-0000-0000-0000-000000000000",
            "source_type": "news",
            "source_name": "Test News",
            "title": "不存在品牌的文章",
            "content": "这篇文章关联了一个不存在的品牌。",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "brand not found",
    }


async def test_duplicate_article_content_returns_conflict(
    client: AsyncClient,
) -> None:
    brand_response = await client.post(
        "/api/v1/brands",
        json={
            "name": "DuplicateArticleBrand",
            "description": "用于测试文章去重",
        },
    )

    assert brand_response.status_code == 201

    payload = {
        "brand_id": brand_response.json()["id"],
        "source_type": "news",
        "source_name": "Test News",
        "title": "重复文章测试",
        "content": "这是一段用于测试重复文章的正文。",
    }

    first_response = await client.post(
        "/api/v1/articles",
        json=payload,
    )
    second_response = await client.post(
        "/api/v1/articles",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "article content already exists",
    }


async def test_get_article_not_found(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/articles/00000000-0000-0000-0000-000000000000",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "article not found",
    }
