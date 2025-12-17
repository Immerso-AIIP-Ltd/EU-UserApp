"""Cache connection setup."""

import json
from hashlib import blake2b
from typing import Any, Dict, Optional

from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError


def query_hash(query_params: Dict[str, Any], digest_size: int = 16) -> str:
    """
    Create a BLAKE2b hash from query parameters.

    Args:
        query_params: Dictionary of query parameters
        digest_size: Hash output size in bytes (default: 16 = 32 hex chars)

    Returns:
        BLAKE2b hash string of the cleaned and sorted query parameters
    """
    # Remove None values
    cleaned_params = {k: v for k, v in query_params.items() if v is not None}

    # Convert to JSON string with sorted keys for consistent hashing
    query_string = json.dumps(cleaned_params, sort_keys=True)

    # Create BLAKE2b hash with custom digest size
    return blake2b(
        query_string.encode(),
        digest_size=digest_size,  # 16 bytes = 32 hex chars (similar to MD5)
    ).hexdigest()


def build_cache_key(template: str, **kwargs: Any) -> str:
    """Build cache key from template and parameters."""
    return template.format(**kwargs)


async def get_cache(redis: Redis, key: str) -> Optional[Dict[str, Any]]:
    """Retrieve data from Redis cache.

    Args:
        redis: Redis client instance
        key: Cache key to retrieve

    Returns:
        Dictionary with cached data if exists, None if cache miss or error
    """
    try:
        cached = await redis.get(key)

        if cached is None:
            logger.debug(f"Cache miss: {key}")
            return None

        data = json.loads(cached)
        logger.debug(f"Cache hit: {key}")
        return data

    except (RedisError, json.JSONDecodeError, UnicodeDecodeError, Exception) as e:
        logger.warning(
            f"Cache get failed for key '{key}': {e.__class__.__name__}: {e!s}",
        )
        return None


async def set_cache(
    redis: Redis,
    key: str,
    data: Any,
    ttl: int = 900,
) -> bool:
    """Set data in Redis cache with expiration.

    Args:
        redis: Redis client instance
        key: Cache key
        data: Data to cache (must be JSON serializable)
        ttl: Time to live in seconds (default 900)

    Returns:
        True if cached successfully, False on error
    """
    try:
        payload = json.dumps(data)
        await redis.setex(key, ttl, payload)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        return True

    except (RedisError, TypeError, ValueError, Exception) as e:
        logger.warning(
            f"Cache set failed for key '{key}': {e.__class__.__name__}: {e!s}",
        )
        return False
