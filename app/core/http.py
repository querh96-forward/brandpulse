from collections.abc import AsyncIterator

from httpx import AsyncClient

from app.core.config import get_settings


async def get_http_client() -> AsyncIterator[AsyncClient]:
    settings = get_settings()

    async with AsyncClient(
        timeout=settings.rss_request_timeout_seconds,
        follow_redirects=True,
    ) as client:
        yield client
