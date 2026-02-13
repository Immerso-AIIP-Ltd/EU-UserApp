"""Cache dependencies."""

from typing import Optional

import redis
from fastapi import Request
from redis.asyncio.cluster import RedisCluster
from redis.asyncio import Redis

from app.settings import settings


def get_redis_connection(request: Request) -> RedisCluster:
    """Get redis connection."""
    return request.app.state.redis_factory.get_connection()


def get_oauth_redis_connection(request: Request) -> RedisCluster:
    """Get oauth redis connection."""
    return request.app.state.oauth_redis_factory.get_connection()
