"""Caching decorators."""

import functools
from typing import Any, Callable

from app.cache.cache_service import CacheService


def cache(
    cache_service: CacheService,
    key_prefix: str,
    expire: int,
) -> Callable[..., Any]:
    """Cache decorator."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            cached_result = await cache_service.get(key)
            if cached_result:
                return cached_result
            result = await func(*args, **kwargs)
            await cache_service.set(key, result, expire=expire)
            return result

        return wrapper

    return decorator
