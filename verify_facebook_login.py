import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.api.v1.social_login.views import facebook_login
from app.api.v1.schemas import SocialLoginRequest
from app.core.exceptions import FacebookAuthError
from fastapi import Request


async def verify():
    print("Starting verification for Facebook Login...")

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
    login_data = SocialLoginRequest(user_id="fb_123", token="valid_fb_token")

    # Mock SocialLoginService.facebook_login
    # We patch it directly on the class
    from app.api.v1.service.social_login_service import SocialLoginService

    original_facebook_login = SocialLoginService.facebook_login

    SocialLoginService.facebook_login = AsyncMock(
        return_value={
            "auth_token": "mocked_fb_auth_token",
            "user": {"user_id": "1", "email": "test@example.com"},
        }
    )

    try:
        response = await facebook_login(
            request=mock_request,
            login_data=login_data,
            db_session=mock_db,
            cache=mock_cache,
            headers=mock_headers,
        )

        body = response.body.decode()
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {body}")

        if response.status_code == 200 and "mocked_fb_auth_token" in body:
            print("SUCCESS: Facebook Login View returned 200 and token.")
        else:
            print("FAILURE: Unexpected response.")

    except Exception as e:
        print(f"FAILURE: Exception occurred: {e}")

    # Test Case 2: Service Error
    print("\nTest 2: Service Error (Auth Failed)")
    SocialLoginService.facebook_login = AsyncMock(side_effect=FacebookAuthError())

    try:
        await facebook_login(
            request=mock_request,
            login_data=login_data,
            db_session=mock_db,
            cache=mock_cache,
            headers=mock_headers,
        )
        print("FAILURE: Exception was not raised.")
    except FacebookAuthError:
        print("SUCCESS: FacebookAuthError raised as expected.")
    except Exception as e:
        print(f"FAILURE: Unexpected exception: {type(e)}")

    # Cleanup
    SocialLoginService.facebook_login = original_facebook_login


if __name__ == "__main__":
    asyncio.run(verify())
