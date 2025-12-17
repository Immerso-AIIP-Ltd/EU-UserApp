"""High-level cache operations."""

from typing import Any, Optional

from redis.asyncio import Redis


class CacheService:
    """Service for cache operations."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get(self, key: str) -> Any:
        """Get value from cache."""
        return await self.redis.get(key)

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set value in cache."""
        await self.redis.set(key, value, ex=expire)

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        await self.redis.delete(key)
