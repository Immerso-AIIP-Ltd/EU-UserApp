"""Redis factory."""

import socket

from redis.asyncio import ConnectionPool, Redis

from app.core.constants import AppUserApp


class RedisFactory:
    """Redis factory."""

    def __init__(self, redis_url: str) -> None:
        self.pool = ConnectionPool.from_url(
            url=redis_url,
            max_connections=AppUserApp.REDIS_MAX_CONNECTIONS,
            socket_connect_timeout=AppUserApp.REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_keepalive=AppUserApp.REDIS_SOCKET_KEEPALIVE,
            socket_keepalive_options={
                socket.TCP_KEEPIDLE: AppUserApp.REDIS_TCP_KEEPIDLE,
                socket.TCP_KEEPINTVL: AppUserApp.REDIS_TCP_KEEPINTVL,
                socket.TCP_KEEPCNT: AppUserApp.REDIS_TCP_KEEPCNT,
            },
            retry_on_timeout=AppUserApp.REDIS_RETRY_ON_TIMEOUT,
            health_check_interval=AppUserApp.REDIS_HEALTH_CHECK_INTERVAL,
            decode_responses=AppUserApp.REDIS_DECODE_RESPONSES,
        )

    def get_connection(self) -> Redis:
        """Get connection."""
        return Redis(connection_pool=self.pool)

    async def close(self) -> None:
        """Close connection."""
        await self.pool.disconnect()
