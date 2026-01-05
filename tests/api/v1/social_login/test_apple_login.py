from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import InvalidSocialToken
from app.main import app


# Mock dependencies
@pytest.fixture
def mock_apple_service():
    with patch("app.api.v1.social_login.views.AppleOAuthService") as MockService:
        service_instance = MockService.return_value
        yield service_instance


@pytest.fixture
def mock_social_login_service():
    with patch(
        "app.api.v1.service.social_login_service.SocialLoginService",
    ) as MockSocialService:
        yield MockSocialService


@pytest.mark.asyncio
async def test_apple_login_success(mock_apple_service, mock_social_login_service):
    # Setup
    mock_apple_service.verify_id_token = AsyncMock()
    mock_social_login_service.apple_login = AsyncMock(
        return_value={
            "auth_token": "valid_token",
            "user": {
                "user_id": "123",
                "email": "test@example.com",
                "name": "Test User",
                "image": None,
            },
        },
    )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/social/apple_login",
            json={"user_id": "apple_123", "token": "valid_apple_token"},
            headers={
                "x-api-client": "ios",
                "x-device-id": "device_123",
                "x-platform": "ios",
                "x-country": "US",
                "x-app-version": "1.0.0",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["auth_token"] == "valid_token"
    assert data["message"] == "User logged in successfully"


@pytest.mark.asyncio
async def test_apple_login_invalid_token(mock_apple_service):
    # Setup - simulate exception during verification of service creation
    # Note: verification happens inside the service.verify_id_token call
    mock_apple_service.verify_id_token = AsyncMock(side_effect=InvalidSocialToken())

    # We need to ensure SocialLoginService calls verify_id_token, so we probably shouldn't mock SocialLoginService entirely
    # OR we can just rely on the fact that if SocialLoginService fails, the view handles it.
    # In integration tests, we'd want to test the full flow. Here we test the view.

    # If we mock SocialLoginService.apple_login to raise the exception, it simulates the service layer failing
    with patch(
        "app.api.v1.service.social_login_service.SocialLoginService.apple_login",
        side_effect=InvalidSocialToken(),
    ):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/social/apple_login",
                json={"user_id": "apple_123", "token": "invalid_token"},
                headers={
                    "x-api-client": "ios",
                    "x-device-id": "device_123",
                    "x-platform": "ios",
                    "x-country": "US",
                    "x-app-version": "1.0.0",
                },
            )

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == 401
