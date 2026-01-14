import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SuccessMessages
from tests.api.test_helper import assert_endpoint_success


@pytest.mark.anyio
async def test_register_with_profile_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "email": "register@example.com",
        "password": "password123",
        "name": "Register User",
        "birth_date": "1990-01-01",
        "gender": "male",
    }
    payload = {"key": "k", "data": "d"}

    with patch(
        "app.api.v1.register.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.register.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.api.v1.register.views._check_user_existence_and_get_state",
        new_callable=AsyncMock,
        return_value="NEW_USER",
    ), patch(
        "app.api.v1.register.views.set_cache",
        new_callable=AsyncMock,
    ):

        data = await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/register/register_with_profile",
            SuccessMessages.USER_CREATED_REDIRECT_OTP,
            payload=payload,
        )
        assert "verify_otp" in data["data"]["redirect_url"]


@pytest.mark.anyio
async def test_verify_otp_register_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "email": "register@example.com",
        "otp": "123456",
        "intent": "registration",
    }
    payload = {"key": "k", "data": "d"}

    mock_cached_data = {
        "email": "register@example.com",
        "password": "hashed_password",
        "name": "Register User",
        "birth_date": "1990-01-01",
    }

    with patch(
        "app.api.v1.register.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.register.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.api.v1.register.views._verify_and_consume_otp",
        new_callable=AsyncMock,
    ), patch(
        "app.api.v1.register.views._get_cached_registration_data",
        new_callable=AsyncMock,
        return_value=mock_cached_data,
    ), patch(
        "app.api.v1.register.views._insert_user_record",
        new_callable=AsyncMock,
    ) as mock_insert, patch(
        "app.api.v1.register.views._create_user_profile",
        new_callable=AsyncMock,
    ), patch(
        "app.api.v1.register.views._log_otp_verification",
        new_callable=AsyncMock,
    ), patch(
        "app.api.v1.register.views._finalize_registration_and_auth",
        new_callable=AsyncMock,
    ) as mock_finalize:

        user_id = uuid.uuid4()
        mock_insert.return_value = [{"id": user_id, "email": "register@example.com"}]
        mock_finalize.return_value = ("mock_token", "mock_refresh_token", 3600)

        data = await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/register/verify_otp_register",
            SuccessMessages.USER_REGISTERED_VERIFIED,
            payload=payload,
        )
        assert data["data"]["id"] == str(user_id)
        assert data["data"]["accesstoken"] == "mock_token"


@pytest.mark.anyio
async def test_resend_otp_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "email": "register@example.com",
        "intent": "registration",
    }
    payload = {"key": "k", "data": "d"}

    with patch(
        "app.api.v1.register.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.register.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.api.v1.register.views.get_cache",
        new_callable=AsyncMock,
        return_value={"some": "data"},
    ), patch(
        "app.api.v1.register.views.GenerateOtpService.generate_otp",
        new_callable=AsyncMock,
    ):

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/register/resend_otp",
            SuccessMessages.OTP_RESENT,
            payload=payload,
        )
