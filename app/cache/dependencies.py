"""Cache dependencies."""

from fastapi import Request
from redis.asyncio import Redis


def get_redis_connection(request: Request) -> Redis:
    """Get redis connection."""
    return request.app.state.redis_factory.get_connection()
