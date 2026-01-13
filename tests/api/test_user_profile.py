from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import UserProfileData
from app.core.constants import SuccessMessages
from app.settings import settings
from tests.api.mock_data import USER_ID, mock_user_profile
from tests.api.test_helper import assert_endpoint_success, get_auth_headers


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Fixture to provide authentication headers."""
    payload = {
        "sub": str(USER_ID),
        "uuid": str(USER_ID),
        "device_id": "device-123",
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm,
    )
    return get_auth_headers(token=token)

@pytest.mark.anyio
async def test_get_user_profile_success(
    client: AsyncClient,
    dbsession: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    mock_profile = mock_user_profile()
    profile_data = UserProfileData.model_validate(
        mock_profile.to_dict(),
    ).model_dump(mode="json")

    with patch(
        "app.api.v1.user_profile.views.get_cache",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.api.v1.user_profile.views.execute_and_transform",
        new_callable=AsyncMock,
        return_value=[profile_data],
    ), patch(
        "app.api.v1.user_profile.views.set_cache", new_callable=AsyncMock,
    ):

        data = await assert_endpoint_success(
            client,
            "GET",
            "/user/v1/auth/user_profile/profile",
            SuccessMessages.USER_PROFILE_RETRIEVED,
            headers=auth_headers,
        )
        assert data["data"]["uuid"] == str(USER_ID)

@pytest.mark.anyio
async def test_update_user_profile_success(
    client: AsyncClient,
    dbsession: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    mock_profile = mock_user_profile(name="Updated Name")
    profile_data = UserProfileData.model_validate(
        mock_profile.to_dict(),
    ).model_dump(mode="json")
    payload = {
        "name": "Updated Name",
        "gender": "M",
        "about_me": "Developer",
        "birth_date": "1990-01-01",
        "nick_name": "Dev",
        "country": "US",
        "avatar_id": 1,
        "profile_image": "http://image.com",
    }

    with patch(
        "app.api.v1.user_profile.views.execute_and_transform",
        new_callable=AsyncMock,
        return_value=[profile_data],
    ), patch(
        "app.api.v1.user_profile.views.set_cache", new_callable=AsyncMock,
    ):

        data = await assert_endpoint_success(
            client,
            "PUT",
            "/user/v1/auth/user_profile/profile",
            SuccessMessages.PROFILE_UPDATED,
            payload=payload,
            headers=auth_headers,
        )
        assert data["data"]["name"] == "Updated Name"

@pytest.mark.anyio
async def test_update_email_mobile_success(
    client: AsyncClient,
    dbsession: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    payload = {
        "email": "new@example.com",
    }

    mock_data = {"email": "new@example.com"}

    with patch(
        "app.api.v1.user_profile.views.execute_and_transform",
        new_callable=AsyncMock,
        return_value=[mock_data],
    ), patch(
        "app.api.v1.user_profile.views.GenerateOtpService.generate_otp",
        new_callable=AsyncMock,
    ):

        data = await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/auth/user_profile/update_email_mobile",
            SuccessMessages.EMAIL_UPDATED,
            payload=payload,
            headers=auth_headers,
        )
        assert "verify_otp" in data["data"]["redirect_url"]
