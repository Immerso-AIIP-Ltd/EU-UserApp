"""Cache dependencies."""

from fastapi import Request
from redis.asyncio.cluster import RedisCluster


def get_redis_connection(request: Request) -> RedisCluster:
    """Get redis connection."""
    return request.app.state.redis_factory.get_connection()


def get_oauth_redis_connection(request: Request) -> RedisCluster:
    """Get oauth redis connection."""
    return request.app.state.oauth_redis_factory.get_connection()
