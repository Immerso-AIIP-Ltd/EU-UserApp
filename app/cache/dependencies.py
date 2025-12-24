"""Cache dependencies."""

from redis.asyncio import Redis
from starlette.requests import Request


def get_redis_connection(request: Request) -> Redis:
    """Get redis connection."""
    return request.app.state.block_redis.get_connection()
