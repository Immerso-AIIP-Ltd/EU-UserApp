from unittest.mock import ANY, AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SuccessMessages
from tests.api.mock_data import USER_ID
from tests.api.test_helper import assert_endpoint_success, get_auth_headers

LOGOUT_ENDPOINT = "/user/v1/auth/user/logout"
DEACTIVATE_ENDPOINT = "/user/v1/auth/user/deactivate"


@pytest.mark.anyio
async def test_logout_success(client: AsyncClient, dbsession: AsyncSession) -> None:
    # Mocks
    mock_user_uuid = str(USER_ID)
    token = "test-token"  # noqa: S105
    headers = get_auth_headers(token=token)

    with patch(
        "app.api.v1.logout.views.AuthService.verify_user_token",
        new_callable=AsyncMock,
    ) as mock_verify, patch(
        "app.api.v1.logout.views.UserLogoutService.logout",
        new_callable=AsyncMock,
    ) as mock_logout:

        mock_verify.return_value = mock_user_uuid

        await assert_endpoint_success(
            client,
            "POST",
            LOGOUT_ENDPOINT,
            SuccessMessages.USER_LOGGED_OUT_SUCCESS,
            headers=headers,
        )

        mock_logout.assert_called_once_with(
            user_uuid=mock_user_uuid,
            token=token,
            device_id=headers["x-device-id"],
            db_session=dbsession,
            cache=ANY,
        )


@pytest.mark.anyio
async def test_deactivate_success(client: AsyncClient, dbsession: AsyncSession) -> None:
    # Mocks
    mock_user_uuid = str(USER_ID)
    token = "test-token"  # noqa: S105
    headers = get_auth_headers(token=token)

    with patch(
        "app.api.v1.logout.views.AuthService.verify_user_token",
        new_callable=AsyncMock,
    ) as mock_verify, patch(
        "app.api.v1.logout.views.UserLogoutService.deactivate_account",
        new_callable=AsyncMock,
    ) as mock_deactivate:

        mock_verify.return_value = mock_user_uuid

        await assert_endpoint_success(
            client,
            "POST",
            DEACTIVATE_ENDPOINT,
            SuccessMessages.USER_DEACTIVATED_SUCCESS,
            headers=headers,
        )

        mock_deactivate.assert_called_once_with(
            user_uuid=mock_user_uuid,
            token=token,
            device_id=headers["x-device-id"],
            db_session=dbsession,
            cache=ANY,
        )
