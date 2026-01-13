import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient
from app.core.constants import HeaderKeys, RequestParams, SuccessMessages

@pytest.fixture
def dbsession() -> AsyncMock:
    return AsyncMock()

@pytest.mark.anyio
async def test_login_success(client: AsyncClient, dbsession: AsyncMock) -> None:
    # Mocks
    mock_decrypted_payload = {
        "email": "test@example.com",
        "password": "password123",
        "calling_code": None,
        "mobile": None
    }
    
    mock_user = {
        "id": 1,
        "email": "test@example.com",
        "name": "Test User",
    }
    
    mock_profile = {
        "user_id": "1",
        "email": "test@example.com",
        "name": "Test User",
        "image": "http://example.com/avatar.jpg"
    }

    mock_token = "mock_auth_token"
    mock_refresh_token = "mock_refresh_token"
    mock_expires_at = 3600

    # Patching dependencies
    with patch("app.api.v1.login.views.SecurityService.decrypt_payload", return_value=mock_decrypted_payload), \
         patch("app.api.v1.login.views.LoginService.login_user", new_callable=AsyncMock) as mock_login_user, \
         patch("app.api.v1.login.views.execute_and_transform", new_callable=AsyncMock) as mock_execute_and_transform:

        mock_login_user.return_value = (mock_user, mock_token, mock_refresh_token, mock_expires_at)
        mock_execute_and_transform.return_value = [mock_profile]

        # Request payload (EncryptedRequest structure, content doesn't matter due to mock)
        payload = {
            "key": "encrypted_key",
            "data": "encrypted_data"
        }

        headers = {
            HeaderKeys.X_DEVICE_ID: "device-123",
            HeaderKeys.X_API_CLIENT: "client-123",
            HeaderKeys.X_PLATFORM: "android",
            HeaderKeys.X_COUNTRY: "US",
            HeaderKeys.X_APP_VERSION: "1.0.0"
        }

        response = await client.post("/user/v1/user/login", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == SuccessMessages.USER_LOGGED_IN
        assert data["data"][RequestParams.AUTH_TOKEN] == mock_token
        assert data["data"][RequestParams.REFRESH_TOKEN] == mock_refresh_token
        assert data["data"][RequestParams.USER][RequestParams.EMAIL] == mock_profile["email"]

@pytest.mark.anyio
async def test_login_bypass_load_test(client: AsyncClient, dbsession: AsyncMock) -> None:
    # Test for load test bypass
    from app.settings import settings
    
    payload = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    headers = {
        HeaderKeys.X_DEVICE_ID: "device-123",
        HeaderKeys.X_API_CLIENT: "client-123",
        HeaderKeys.X_LOAD_TEST_BYPASS: settings.load_test_bypass_secret,
        HeaderKeys.X_PLATFORM: "android",
        HeaderKeys.X_COUNTRY: "US",
        HeaderKeys.X_APP_VERSION: "1.0.0"
    }

    mock_user_row = {
        "id": 1,
        "email": "test@example.com",
        "name": "Test User"
    }

    with patch("app.api.v1.login.views.execute_query", new_callable=AsyncMock) as mock_execute_query:
        # Mocking database response for user fetch
        mock_execute_query.return_value = [mock_user_row]

        response = await client.post("/user/v1/user/login", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"][RequestParams.USER][RequestParams.NAME] == "Load Test User"

@pytest.mark.anyio
async def test_forgot_password_success(client: AsyncClient, dbsession: AsyncMock) -> None:
    mock_decrypted = {"email": "test@example.com"}
    payload = {"key": "k", "data": "d"}
    headers = {
        HeaderKeys.X_DEVICE_ID: "dev",
        HeaderKeys.X_API_CLIENT: "cli",
        HeaderKeys.X_PLATFORM: "android",
        HeaderKeys.X_COUNTRY: "US",
        HeaderKeys.X_APP_VERSION: "1"
    }

    with patch("app.api.v1.login.views.SecurityService.decrypt_payload", return_value=mock_decrypted), \
         patch("app.api.v1.login.views.ForgotPasswordService.forgot_password_email", new_callable=AsyncMock) as mock_service:
        
        mock_service.return_value = "Reset link sent"
        response = await client.post("/user/v1/user/forgot_password", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "Reset link sent"

@pytest.mark.anyio
async def test_set_forgot_password_success(client: AsyncClient, dbsession: AsyncMock) -> None:
    mock_decrypted = {"email": "test@example.com", "password": "newpassword123"}
    payload = {"key": "k", "data": "d"}
    headers = {
        HeaderKeys.X_DEVICE_ID: "dev",
        HeaderKeys.X_API_CLIENT: "cli",
        HeaderKeys.X_PLATFORM: "android",
        HeaderKeys.X_COUNTRY: "US",
        HeaderKeys.X_APP_VERSION: "1"
    }

    with patch("app.api.v1.login.views.SecurityService.decrypt_payload", return_value=mock_decrypted), \
         patch("app.api.v1.login.views.ForgotPasswordService.set_forgot_password", new_callable=AsyncMock) as mock_service:
        
        mock_service.return_value = ("mock_token", "2026-01-01")
        response = await client.post("/user/v1/user/set_forgot_password", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["auth_token"] == "mock_token"

@pytest.mark.anyio
async def test_change_password_success(client: AsyncClient, dbsession: AsyncMock) -> None:
    payload = {"new_password": "p1", "new_password_confirm": "p1"}
    headers = {
        HeaderKeys.X_DEVICE_ID: "dev",
        HeaderKeys.X_API_CLIENT: "cli",
        HeaderKeys.X_PLATFORM: "android",
        HeaderKeys.X_COUNTRY: "US",
        HeaderKeys.X_APP_VERSION: "1",
        HeaderKeys.X_API_TOKEN: "token"
    }

    with patch("app.api.v1.login.views.AuthService.verify_user_token", new_callable=AsyncMock) as mock_verify, \
         patch("app.api.v1.login.views.ChangePasswordService.change_password", new_callable=AsyncMock) as mock_change:
        
        mock_verify.return_value = "user-uuid"
        response = await client.put("/user/v1/user/change_password", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == SuccessMessages.PASSWORD_CHANGED_SUCCESS

@pytest.mark.anyio
async def test_refresh_token_success(client: AsyncClient, dbsession: AsyncMock) -> None:
    payload = {"refresh_token": "rt"}
    headers = {
        HeaderKeys.X_DEVICE_ID: "dev",
        HeaderKeys.X_API_CLIENT: "cli",
        HeaderKeys.X_PLATFORM: "android",
        HeaderKeys.X_COUNTRY: "US",
        HeaderKeys.X_APP_VERSION: "1"
    }

    with patch("app.api.v1.login.views.AuthService.refresh_access_token", new_callable=AsyncMock) as mock_refresh:
        mock_refresh.return_value = ("new_at", "new_rt", "expiry")
        response = await client.post("/user/v1/user/refresh_token", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.json()["data"][RequestParams.AUTH_TOKEN] == "new_at"
