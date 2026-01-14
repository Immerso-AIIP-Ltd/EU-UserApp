from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RequestParams, SuccessMessages
from tests.api.mock_data import mock_user
from tests.api.test_helper import assert_endpoint_success, get_auth_headers

LOGIN_ENDPOINT = "/user/v1/user/login"


@pytest.mark.anyio
async def test_login_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    # Mocks
    mock_decrypted_payload = {
        "email": "test@example.com",
        "password": "password123",
        "calling_code": None,
        "mobile": None,
    }

    user = mock_user()

    mock_token = "mock_auth_token"  # noqa: S105
    mock_refresh_token = "mock_refresh_token"  # noqa: S105
    mock_expires_at = 3600

    # DB mocks
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user

    mock_profile_result = MagicMock()
    mock_profile_result.mappings.return_value.all.return_value = [
        {"email": "test@example.com"},
    ]

    # Patching dependencies
    with patch(
        "app.api.v1.login.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted_payload,
    ), patch(
        "app.api.v1.login.views.LoginService.login_user",
        new_callable=AsyncMock,
    ) as mock_login_user, patch(
        "app.api.v1.login.views.execute_and_transform",
        new_callable=AsyncMock,
    ) as mock_execute_and_transform:

        mock_login_user.return_value = (
            user,
            mock_token,
            mock_refresh_token,
            mock_expires_at,
        )
        mock_execute_and_transform.return_value = [{"email": "test@example.com"}]

        payload = {"key": "k", "data": "d"}

        data = await assert_endpoint_success(
            client,
            "POST",
            LOGIN_ENDPOINT,
            SuccessMessages.USER_LOGGED_IN,
            payload=payload,
        )

        assert data["data"][RequestParams.AUTH_TOKEN] == mock_token
        assert data["data"][RequestParams.REFRESH_TOKEN] == mock_refresh_token
        assert (
            data["data"][RequestParams.USER][RequestParams.EMAIL] == "test@example.com"
        )


@pytest.mark.anyio
async def test_login_bypass_load_test(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    from app.settings import settings

    mock_decrypted_payload = {
        "email": "test@example.com",
        "password": "password123",
        "calling_code": None,
        "mobile": None,
    }

    payload = {"key": "k", "data": "d"}

    headers = get_auth_headers()
    headers["x-load-test-bypass"] = settings.load_test_bypass_secret

    mock_user_row = {"id": 1, "email": "test@example.com", "name": "Test User"}

    with patch(
        "app.api.v1.login.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted_payload,
    ), patch(
        "app.api.v1.login.views.execute_query",
        new_callable=AsyncMock,
    ) as mock_execute_query:
        mock_execute_query.return_value = [mock_user_row]

        data = await assert_endpoint_success(
            client,
            "POST",
            LOGIN_ENDPOINT,
            SuccessMessages.USER_LOGGED_IN,
            payload=payload,
            headers=headers,
        )
        assert data["data"][RequestParams.USER][RequestParams.NAME] == "Load Test User"


@pytest.mark.anyio
async def test_forgot_password_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {"email": "test@example.com"}
    payload = {"key": "k", "data": "d"}

    with patch(
        "app.api.v1.login.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.login.views.ForgotPasswordService.forgot_password_email",
        new_callable=AsyncMock,
    ) as mock_service, patch(
        "app.api.v1.login.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=True,
    ):

        mock_service.return_value = "Reset link sent"
        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/user/forgot_password",
            "Reset link sent",
            payload=payload,
        )


@pytest.mark.anyio
async def test_set_forgot_password_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {"email": "test@example.com", "password": "newpassword123"}
    payload = {"key": "k", "data": "d"}

    with patch(
        "app.api.v1.login.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.login.views.ForgotPasswordService.set_forgot_password",
        new_callable=AsyncMock,
    ) as mock_service:

        mock_service.return_value = ("mock_token", "mock_refresh_token", 3600)
        data = await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/user/set_forgot_password",
            SuccessMessages.PASSWORD_RESET_SUCCESS,
            payload=payload,
        )
        assert data["data"]["auth_token"] == "mock_token"  # noqa: S105


@pytest.mark.anyio
async def test_change_password_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    import uuid

    payload = {"new_password": "p1", "new_password_confirm": "p1"}
    headers = get_auth_headers(token="valid_token")  # noqa: S106

    with patch(
        "app.api.v1.login.views.AuthService.verify_user_token",
        new_callable=AsyncMock,
    ) as mock_verify, patch(
        "app.api.v1.login.views.ChangePasswordService.change_password",
        new_callable=AsyncMock,
    ) as _:

        mock_verify.return_value = str(uuid.uuid4())
        await assert_endpoint_success(
            client,
            "PUT",
            "/user/v1/user/change_password",
            SuccessMessages.PASSWORD_CHANGED_SUCCESS,
            payload=payload,
            headers=headers,
        )


@pytest.mark.anyio
async def test_refresh_token_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    payload = {"refresh_token": "rt"}

    with patch(
        "app.api.v1.login.views.AuthService.refresh_access_token",
        new_callable=AsyncMock,
    ) as mock_refresh, patch(
        "app.api.v1.login.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=True,
    ):

        mock_refresh.return_value = ("new_at", "new_rt", "expiry")
        data = await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/user/refresh_token",
            SuccessMessages.TOKEN_REFRESHED_SUCCESSFULLY,
            payload=payload,
        )
        assert data["data"][RequestParams.AUTH_TOKEN] == "new_at"
