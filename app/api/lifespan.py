from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.cache.factory import RedisFactory
from app.core.constants import AppUserApp
from app.db.factory import DatabaseFactory
from app.settings import settings


@asynccontextmanager
async def lifespan_setup(
    app: FastAPI,
) -> AsyncGenerator[None, None]:  # pragma: no cover
    """
    Actions to run on application startup.

    This function uses fastAPI app to store data
    in the state, such as db_engine.

    :param app: the fastAPI application.
    :return: function that actually performs actions.
    """
    app.middleware_stack = None
    db_factory = DatabaseFactory(str(settings.db_url), settings.db_echo)
    
    cluster_nodes = settings.redis_cluster_nodes
    if not cluster_nodes:
        raise ValueError("Redis cluster nodes configuration is missing")
    
    redis_factory = RedisFactory(
        cluster_nodes=cluster_nodes,
        password=settings.redis_pass,
        socket_timeout=settings.redis_socket_timeout,
        decode_responses=True,
        socket_connect_timeout=AppUserApp.REDIS_SOCKET_CONNECT_TIMEOUT,
        health_check_interval=AppUserApp.REDIS_HEALTH_CHECK_INTERVAL,
        max_connections=AppUserApp.REDIS_MAX_CONNECTIONS,
    )
    
    oauth_redis_factory = RedisFactory(
        cluster_nodes=settings.oauth_redis_cluster_nodes or cluster_nodes,
        password=settings.oauth_redis_pass,
        socket_timeout=settings.oauth_redis_socket_timeout,
        decode_responses=True,
        socket_connect_timeout=AppUserApp.REDIS_SOCKET_CONNECT_TIMEOUT,
        health_check_interval=AppUserApp.REDIS_HEALTH_CHECK_INTERVAL,
        max_connections=AppUserApp.REDIS_MAX_CONNECTIONS,
    )

    app.state.db_factory = db_factory
    app.state.redis_factory = redis_factory
    app.state.oauth_redis_factory = oauth_redis_factory
    app.state.db_session_factory = db_factory.get_session
    
    app.middleware_stack = app.build_middleware_stack()

    from app.utils.kafka_producer import KafkaProducerService

    await KafkaProducerService.start()

    try:
        yield
    finally:
        await KafkaProducerService.stop()
        await app.state.db_factory.close()
        await app.state.redis_factory.close()
        await app.state.oauth_redis_factory.close()
