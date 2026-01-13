import pytest
from httpx import AsyncClient

from app.core.constants import SuccessMessages
from tests.api.test_helper import assert_endpoint_success


@pytest.mark.anyio
async def test_health_success(client: AsyncClient) -> None:
    await assert_endpoint_success(
        client,
        "GET",
        "/user/v1/internal/monitoring/health",
        SuccessMessages.HEALTH_CHECKUP,
    )

@pytest.mark.anyio
async def test_redis_health_success(client: AsyncClient) -> None:
    # Redis is mocked in conftest, so ping should succeed
    await assert_endpoint_success(
        client,
        "GET",
        "/user/v1/internal/monitoring/redis_health",
        SuccessMessages.HEALTH_CHECKUP,
    )
