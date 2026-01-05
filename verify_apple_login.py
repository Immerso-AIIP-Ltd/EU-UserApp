import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.api.v1.social_login.views import apple_login
from app.api.v1.schemas import SocialLoginRequest
from app.core.exceptions import InvalidSocialToken
from fastapi import Request


async def verify():
    print("Starting verification...")

    # Mock dependencies
    mock_db = AsyncMock()
    mock_cache = AsyncMock()

    # Mock Request
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"User-Agent": "TestAgent"}

    # Mock Headers dependency result
    mock_headers = {
        "api_client": "ios",
        "device_id": "test_device",
        "platform": "ios",
        "country": "US",
    }

    # Test Case 1: Success
    print("\nTest 1: Success Flow")
    login_data = SocialLoginRequest(user_id="apple_123", token="valid_token")

    # Mock SocialLoginService
    from app.api.v1.service.social_login_service import SocialLoginService

    original_apple_login = SocialLoginService.apple_login

    SocialLoginService.apple_login = AsyncMock(
        return_value={
            "auth_token": "mocked_auth_token",
            "user": {"user_id": "1", "email": "test@example.com"},
        }
    )

    try:
        response = await apple_login(
            request=mock_request,
            login_data=login_data,
            db_session=mock_db,
            cache=mock_cache,
            headers=mock_headers,
        )

        body = response.body.decode()
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {body}")

        if response.status_code == 200 and "mocked_auth_token" in body:
            print("SUCCESS: Apple Login View returned 200 and token.")
        else:
            print("FAILURE: Unexpected response.")

    except Exception as e:
        print(f"FAILURE: Exception occurred: {e}")

    # Test Case 2: Service Error
    print("\nTest 2: Service Error (Invalid Token)")
    SocialLoginService.apple_login = AsyncMock(side_effect=InvalidSocialToken())

    try:
        # The view doesn't catch the exception, it propagates to FastAPI's exception handler.
        # So calling it directly should raise the exception.
        await apple_login(
            request=mock_request,
            login_data=login_data,
            db_session=mock_db,
            cache=mock_cache,
            headers=mock_headers,
        )
        print("FAILURE: Exception was not raised.")
    except InvalidSocialToken:
        print("SUCCESS: InvalidSocialToken raised as expected.")
    except Exception as e:
        print(f"FAILURE: Unexpected exception: {type(e)}")

    # Cleanup
    SocialLoginService.apple_login = original_apple_login


if __name__ == "__main__":
    asyncio.run(verify())
