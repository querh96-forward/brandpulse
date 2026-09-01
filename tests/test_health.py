from datetime import datetime

from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


async def test_root_returns_project_metadata(client: AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }


async def test_health_check_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] == settings.app_env
    assert set(data) == {"status", "environment", "timestamp"}

    timestamp = datetime.fromisoformat(data["timestamp"])
    assert timestamp.tzinfo is not None


async def test_project_info_returns_metadata(client: AsyncClient) -> None:
    response = await client.get("/api/v1/info")

    assert response.status_code == 200
    assert response.json() == {
        "project": "BrandPulse",
        "version": "0.1.0",
        "environment": settings.app_env,
    }


async def test_cors_preflight_allows_frontend(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/articles",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ("http://localhost:5173")
    assert "POST" in response.headers["access-control-allow-methods"]
