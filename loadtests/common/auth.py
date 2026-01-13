import random
import string

from app.core.constants import HeaderKeys, Intents


def get_bypass_headers() -> dict[str, str]:
    """Return headers for load test bypass."""
    return {HeaderKeys.X_LOAD_TEST_BYPASS: "LOAD_TEST_BYPASS_SECRET_123"}


def register_and_login(client, headers):
    """
    Complete registration and login flow for load tests.
    Uses bypass header to skip physical OTP/Redis.
    """
    email = (
        f"loadtest_{''.join(random.choices(string.ascii_lowercase, k=10))}@example.com"
    )
    password = "Password123!"

    # 1. Register
    reg_payload = {
        "email": email,
        "password": password,
        "name": "Load Test User",
        "birth_date": "1990-01-01",
        "gender": "M",
    }
    with client.post(
        "/user/v1/register/register_with_profile",
        json=reg_payload,
        headers=headers,
        catch_response=True,
    ) as resp:
        if resp.status_code != 200:
            resp.failure(f"Setup: Registration failed: {resp.text}")
            return None, None

    # 2. Verify OTP (Using Bypass)
    verify_payload = {
        "email": email,
        "otp": "loadtest-bypass",
        "intent": Intents.REGISTRATION,
    }
    bypass_headers = {**headers, **get_bypass_headers()}
    with client.post(
        "/user/v1/register/verify_otp_register",
        json=verify_payload,
        headers=bypass_headers,
        catch_response=True,
    ) as resp:
        if resp.status_code != 200:
            resp.failure(f"Setup: OTP verification bypass failed: {resp.text}")
            return None, None

    # 3. Login
    login_payload = {"email": email, "password": password, "login_type": "email"}
    with client.post(
        "/user/v1/user/login",
        json=login_payload,
        headers=bypass_headers,
        catch_response=True,
    ) as resp:
        if resp.status_code == 200:
            # Login returns 'token' or 'auth_token' inside 'data'
            data = resp.json().get("data", {})
            auth_token = data.get("token") or data.get("auth_token")
            return email, auth_token
        else:
            resp.failure(f"Setup: Login failed: {resp.text}")
            return None, None
