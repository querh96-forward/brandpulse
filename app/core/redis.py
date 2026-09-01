from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.core.config import get_settings


async def get_redis_client() -> AsyncIterator[Redis]:
    settings = get_settings()

    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        yield redis_client
    finally:
        await redis_client.aclose()
