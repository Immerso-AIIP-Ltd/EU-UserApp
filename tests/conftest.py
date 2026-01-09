from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeServer
from fakeredis.aioredis import FakeConnection, FakeRedis
from fastapi import FastAPI
from httpx import AsyncClient
from loguru import logger
from redis.asyncio import ConnectionPool
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.application import get_app
from app.cache.dependencies import get_redis_connection
from app.db.dependencies import get_db_session
from app.db.meta import meta
from app.db.models import load_all_models
from app.db.utils import create_database, drop_database
from app.settings import settings


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


@pytest.fixture(scope="session")
async def _engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create engine and databases.

    :yield: new engine.
    """

    load_all_models()

    try:
        await create_database()
        engine = create_async_engine(str(settings.db_url_pytest))
        async with engine.begin() as conn:
            # Create schemas first
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS user_app"))
            await conn.run_sync(meta.create_all)

        yield engine
        await engine.dispose()
        await drop_database()
    except (OperationalError, Exception) as e:
        logger.warning(f"Database setup failed (Postgres might not be running): {e}")
        # Yield a dummy engine if we can't connect, tests using mocks will still work
        engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/dummy")
        yield engine
        await engine.dispose()


@pytest.fixture
async def dbsession(
    _engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get session to database.

    Fixture that returns a SQLAlchemy session with a SAVEPOINT, and the rollback to it
    after the test completes.

    :param _engine: current engine.
    :yields: async session.
    """
    connection = await _engine.connect()
    trans = await connection.begin()

    session_maker = async_sessionmaker(
        connection,
        expire_on_commit=False,
    )
    session = session_maker()

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


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
def fastapi_app(
    dbsession: AsyncSession,
    fake_redis_client: FakeRedis,
) -> FastAPI:
    """
    Fixture for creating FastAPI app.

    :return: fastapi app with mocked dependencies.
    """
    application = get_app()
    application.dependency_overrides[get_db_session] = lambda: dbsession
    application.dependency_overrides[get_redis_connection] = lambda: fake_redis_client
    return application


@pytest.fixture
async def client(
    fastapi_app: FastAPI,
    anyio_backend: Any,
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


@pytest.fixture
def mock_db_session(fastapi_app: FastAPI) -> AsyncMock:
    """Fixture to mock the database session."""
    mock_db = AsyncMock()
    fastapi_app.dependency_overrides[get_db_session] = lambda: mock_db
    return mock_db
