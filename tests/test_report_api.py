import uuid

from httpx import AsyncClient


async def test_get_brand_risk_summary(
    client: AsyncClient,
) -> None:
    brand_response = await client.post(
        "/api/v1/brands",
        json={
            "name": "Summary API Test Brand",
            "description": "用于测试风险汇总接口",
        },
    )

    assert brand_response.status_code == 201
    brand_id = brand_response.json()["id"]

    summary_response = await client.get(
        f"/api/v1/brands/{brand_id}/risk-summary",
    )

    assert summary_response.status_code == 200
    assert summary_response.json() == {
        "brand_id": brand_id,
        "total_articles": 0,
        "analyzed_articles": 0,
        "high_risk_articles": 0,
        "average_risk_score": 0.0,
        "positive_articles": 0,
        "neutral_articles": 0,
        "negative_articles": 0,
    }

    high_risk_response = await client.get(
        f"/api/v1/brands/{brand_id}/high-risk-articles",
        params={
            "offset": 0,
            "limit": 20,
        },
    )

    assert high_risk_response.status_code == 200
    assert high_risk_response.json() == []

    invalid_pagination_response = await client.get(
        f"/api/v1/brands/{brand_id}/high-risk-articles",
        params={
            "offset": -1,
            "limit": 20,
        },
    )

    assert invalid_pagination_response.status_code == 422

    trend_response = await client.get(
        f"/api/v1/brands/{brand_id}/risk-trend",
        params={"days": 30},
    )

    assert trend_response.status_code == 200
    assert trend_response.json() == []

    invalid_days_response = await client.get(
        f"/api/v1/brands/{brand_id}/risk-trend",
        params={"days": 0},
    )

    assert invalid_days_response.status_code == 422

    missing_brand_id = uuid.uuid4()

    not_found_response = await client.get(
        f"/api/v1/brands/{missing_brand_id}/risk-summary",
    )

    assert not_found_response.status_code == 404
    assert not_found_response.json() == {
        "detail": "brand not found",
    }

    missing_list_response = await client.get(
        f"/api/v1/brands/{missing_brand_id}/high-risk-articles",
    )

    assert missing_list_response.status_code == 404
    assert missing_list_response.json() == {
        "detail": "brand not found",
    }

    missing_trend_response = await client.get(
        f"/api/v1/brands/{missing_brand_id}/risk-trend",
        params={"days": 30},
    )

    assert missing_trend_response.status_code == 404
    assert missing_trend_response.json() == {
        "detail": "brand not found",
    }
