from collections.abc import AsyncIterator

from httpx import AsyncClient


async def get_http_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        timeout=10.0,
        follow_redirects=True,
    ) as client:
        yield client
