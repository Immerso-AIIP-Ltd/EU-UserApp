import pytest
from unittest.mock import AsyncMock, patch, ANY
from httpx import AsyncClient
from app.core.constants import HeaderKeys, SuccessMessages

@pytest.fixture
def dbsession() -> AsyncMock:
    return AsyncMock()

@pytest.mark.anyio
async def test_logout_success(client: AsyncClient, dbsession: AsyncMock) -> None:
    # Mocks
    mock_user_id = "test-user-uuid"
    
    headers = {
        HeaderKeys.X_API_CLIENT: "test-client",
        HeaderKeys.X_DEVICE_ID: "test-device",
        HeaderKeys.X_PLATFORM: "android",
        HeaderKeys.X_COUNTRY: "US",
        HeaderKeys.X_APP_VERSION: "1.0.0",
        HeaderKeys.X_API_TOKEN: "test-token"
    }

    with patch("app.api.v1.logout.views.AuthService.verify_user_token", new_callable=AsyncMock) as mock_verify, \
         patch("app.api.v1.logout.views.UserLogoutService.logout", new_callable=AsyncMock) as mock_logout:
        
        mock_verify.return_value = mock_user_id
        
        response = await client.post("/user/v1/auth/user/logout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == SuccessMessages.USER_LOGGED_OUT_SUCCESS
        
        mock_logout.assert_called_once_with(
            user_uuid=mock_user_id,
            token="test-token",
            device_id="test-device",
            db_session=dbsession,
            cache=ANY
        )

@pytest.mark.anyio
async def test_deactivate_success(client: AsyncClient, dbsession: AsyncMock) -> None:
    # Mocks
    mock_user_id = "test-user-uuid"
    
    headers = {
        HeaderKeys.X_API_CLIENT: "test-client",
        HeaderKeys.X_DEVICE_ID: "test-device",
        HeaderKeys.X_PLATFORM: "android",
        HeaderKeys.X_COUNTRY: "US",
        HeaderKeys.X_APP_VERSION: "1.0.0",
        HeaderKeys.X_API_TOKEN: "test-token"
    }

    with patch("app.api.v1.logout.views.AuthService.verify_user_token", new_callable=AsyncMock) as mock_verify, \
         patch("app.api.v1.logout.views.UserLogoutService.deactivate_account", new_callable=AsyncMock) as mock_deactivate:
        
        mock_verify.return_value = mock_user_id
        
        response = await client.post("/user/v1/auth/user/deactivate", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == SuccessMessages.USER_DEACTIVATED_SUCCESS
        
        mock_deactivate.assert_called_once_with(
            user_uuid=mock_user_id,
            token="test-token",
            device_id="test-device",
            db_session=dbsession,
            cache=ANY
        )
