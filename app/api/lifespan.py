from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.cache.factory import RedisFactory
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
    redis_factory = RedisFactory(str(settings.redis_url))
    app.state.redis_factory = redis_factory
    app.middleware_stack = app.build_middleware_stack()
    app.state.db_factory = DatabaseFactory(
        db_url=str(settings.db_url),
        db_echo=settings.db_echo,
    )

    app.middleware_stack = app.build_middleware_stack()

    try:
        yield
    finally:
        await app.state.redis_factory.close()
        await app.state.db_factory.close()
