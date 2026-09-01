import uuid

from httpx import AsyncClient


async def test_create_list_and_get_brand(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/brands",
        json={
            "name": "TestBrand",
            "description": "自动化测试品牌",
        },
    )

    assert create_response.status_code == 201

    created_brand = create_response.json()
    brand_id = created_brand["id"]

    assert created_brand["name"] == "TestBrand"
    assert created_brand["description"] == "自动化测试品牌"
    assert uuid.UUID(brand_id)

    list_response = await client.get(
        "/api/v1/brands",
        params={"offset": 0, "limit": 20},
    )

    assert list_response.status_code == 200

    brands = list_response.json()
    assert any(brand["id"] == brand_id for brand in brands)

    detail_response = await client.get(f"/api/v1/brands/{brand_id}")

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == brand_id


async def test_duplicate_brand_returns_conflict(client: AsyncClient) -> None:
    payload = {
        "name": "DuplicateBrand",
        "description": "重复品牌测试",
    }

    first_response = await client.post("/api/v1/brands", json=payload)
    second_response = await client.post("/api/v1/brands", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "brand name already exists",
    }


async def test_brand_validation_and_not_found(client: AsyncClient) -> None:
    blank_name_response = await client.post(
        "/api/v1/brands",
        json={
            "name": "   ",
            "description": "无效品牌",
        },
    )

    assert blank_name_response.status_code == 422

    not_found_response = await client.get("/api/v1/brands/00000000-0000-0000-0000-000000000000")

    assert not_found_response.status_code == 404
    assert not_found_response.json() == {
        "detail": "brand not found",
    }

    invalid_uuid_response = await client.get("/api/v1/brands/abc")

    assert invalid_uuid_response.status_code == 422
