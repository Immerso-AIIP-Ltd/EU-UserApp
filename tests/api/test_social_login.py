from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SuccessMessages
from tests.api.test_helper import assert_endpoint_success


@pytest.mark.anyio
async def test_google_login_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "uid": "google_uid",
        "id_token": "google_token",
    }
    payload = {"key": "k", "data": "d"}
    mock_auth_data = {
        "accessToken": "mock_access_token",
        "refreshToken": "mock_refresh_token",
        "token_expiry": 3600,
    }

    with patch(
        "app.api.v1.social_login.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.social_login.views.SocialLoginService.google_login",
        new_callable=AsyncMock,
        return_value=mock_auth_data,
    ):

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/social/google_login",
            SuccessMessages.USER_LOGGED_IN,
            payload=payload,
        )


@pytest.mark.anyio
async def test_apple_login_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "uid": "apple_uid",
        "id_token": "apple_token",
    }
    payload = {"key": "k", "data": "d"}
    mock_auth_data = {
        "accessToken": "mock_access_token",
        "refreshToken": "mock_refresh_token",
        "token_expiry": 3600,
    }

    with patch(
        "app.api.v1.social_login.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.social_login.views.SocialLoginService.apple_login",
        new_callable=AsyncMock,
        return_value=mock_auth_data,
    ):

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/social/apple_login",
            SuccessMessages.USER_LOGGED_IN,
            payload=payload,
        )


@pytest.mark.anyio
async def test_facebook_login_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "uid": "facebook_uid",
        "access_token": "facebook_token",
    }
    payload = {"key": "k", "data": "d"}
    mock_auth_data = {
        "accessToken": "mock_access_token",
        "refreshToken": "mock_refresh_token",
        "token_expiry": 3600,
    }

    with patch(
        "app.api.v1.social_login.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.social_login.views.SocialLoginService.facebook_login",
        new_callable=AsyncMock,
        return_value=mock_auth_data,
    ):

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/social/facebook_login",
            SuccessMessages.USER_LOGGED_IN,
            payload=payload,
        )
