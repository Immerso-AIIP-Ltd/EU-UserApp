from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeServer
from fakeredis.aioredis import FakeConnection, FakeRedis
from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import ConnectionPool

from app.api.application import get_app
from app.cache.dependencies import get_redis_connection


@pytest.fixture(autouse=True)
def disable_cache_for_non_config_tests(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    if "configurations" in request.node.nodeid:
        return

    async def _fake_get_cache(*args: Any, **kwargs: Any) -> None:
        return None

    async def _fake_set_cache(*args: Any, **kwargs: Any) -> None:
        return None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """
    Backend for anyio pytest plugin.

    :return: backend name.
    """
    return "asyncio"


@pytest.fixture
async def fake_redis_client() -> AsyncGenerator[FakeRedis, None]:
    """
    Get instance of a fake redis client.

    :yield: FakeRedis instance.
    """
    server = FakeServer()
    server.connected = True
    client = FakeRedis(
        connection_pool=ConnectionPool(connection_class=FakeConnection, server=server),
    )
    await client.flushall()

    yield client

    await client.close()


@pytest.fixture
def fastapi_app() -> FastAPI:
    """
    Fixture for creating FastAPI app.

    :return: fastapi app.
    """
    application = get_app()
    application.dependency_overrides[get_redis_connection] = lambda: fake_redis_client
    return application


@pytest.fixture
async def client(
    fastapi_app: FastAPI,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture that creates client for requesting server.

    :param fastapi_app: the application.
    :yield: client for the app.
    """
    async with AsyncClient(app=fastapi_app, base_url="http://test", timeout=2.0) as ac:
        yield ac


@pytest.fixture
def mock_redis_session() -> AsyncMock:
    """Fixture for a mock redis session."""
    return AsyncMock()


@pytest.fixture(autouse=True)
def override_dependencies(
    fastapi_app: FastAPI,
    mock_redis_session: AsyncMock,
) -> Any:
    """Fixture to automatically clean up dependency overrides after each test."""
    original_overrides = fastapi_app.dependency_overrides.copy()
    fastapi_app.dependency_overrides[get_redis_connection] = lambda: mock_redis_session
    yield
    fastapi_app.dependency_overrides = original_overrides
