from typing import Any

from redis.asyncio.cluster import ClusterNode, RedisCluster


class RedisFactory:
    """Redis Cluster factory."""

    def __init__(
        self,
        cluster_nodes: str,
        password: str | None,
        socket_timeout: int,
        decode_responses: bool = True,
        socket_connect_timeout: int = 2,
        health_check_interval: int = 0,
        max_connections: int = 50,
    ) -> None:
        startup_nodes = [
            ClusterNode(host, int(port))
            for host, port in (node.split(":") for node in cluster_nodes.split(","))
        ]
        kwargs: dict[str, Any] = {
            "startup_nodes": startup_nodes,
            "decode_responses": decode_responses,
            "socket_connect_timeout": socket_connect_timeout,
            "socket_timeout": socket_timeout,
            "health_check_interval": health_check_interval,
            "max_connections": max_connections,
        }
        if password:
            kwargs["password"] = password

        self.client = RedisCluster(**kwargs)  # type: ignore[abstract]

    def get_connection(self) -> RedisCluster:
        """Get Redis Cluster client."""
        return self.client

    async def close(self) -> None:
        """Close Redis connections."""
        await self.client.close()
