import random
import string
import redis
from app.core.constants import CacheKeyTemplates, Intents


def register_and_login(client, headers):
    """
    Complete registration and login flow for load tests.
    1. Register
    2. Fetch OTP from Redis
    3. Verify OTP
    4. Login
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
        "gender": "male",
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

    # 2. Fetch OTP from Redis
    try:
        import os
        from app.settings import settings

        redis_pass = os.getenv("APP_REDIS_PASS") or settings.redis_pass
        redis_host_env = os.getenv("APP_REDIS_HOST")

        # Try localhost first (exposed port), then try environment host (if reachable)
        hosts_to_try = [
            {"host": "localhost", "port": 6379},
            {"host": "localhost", "port": 6380},
        ]
        if redis_host_env and redis_host_env != "app-redis":
            hosts_to_try.append({"host": redis_host_env, "port": 6379})

        otp = None
        for target in hosts_to_try:
            # Try combinations:
            # 1. default user + password (common for Redis 6+)
            # 2. No user + password (legacy)
            # 3. No user + no password
            auth_configs = [
                {"username": "default", "password": redis_pass},
                {"password": redis_pass},
                {"password": None},
            ]
            for config in auth_configs:
                try:
                    r = redis.Redis(
                        host=target["host"],
                        port=target["port"],
                        db=0,
                        decode_responses=True,
                        socket_timeout=2,
                        **config,
                    )
                    # Key template from constants.py: "email_otp_{receiver}_{intent}"
                    otp_key = CacheKeyTemplates.OTP_EMAIL.format(
                        receiver=email, intent=Intents.REGISTRATION
                    )
                    otp = r.get(otp_key)
                    if otp:
                        break
                    # Even if no OTP, if ping works, we might just be looking at the wrong key
                    if r.ping():
                        print(
                            f"DEBUG: Connected to Redis at {target['host']}:{target['port']} with config {config}, but OTP not found for {email}"
                        )
                except Exception as host_e:
                    pass  # Silent failure to try next config
            if otp:
                break

        if not otp:
            print(
                f"DEBUG: OTP not found in Redis for {email} after trying {hosts_to_try}"
            )
            return None, None
    except Exception as e:
        print(f"Setup: Redis retrieval failed: {e}")
        return None, None

    # 3. Verify OTP
    verify_payload = {
        "email": email,
        "otp": otp,
        "intent": Intents.REGISTRATION,
    }
    with client.post(
        "/user/v1/register/verify_otp_register",
        json=verify_payload,
        headers=headers,
        catch_response=True,
    ) as resp:
        if resp.status_code != 200:
            resp.failure(f"Setup: OTP verification failed: {resp.text}")
            return None, None

    # 4. Login
    login_payload = {"email": email, "password": password, "login_type": "email"}
    with client.post(
        "/user/v1/user/login",
        json=login_payload,
        headers=headers,
        catch_response=True,
    ) as resp:
        if resp.status_code == 200:
            auth_token = (
                resp.json().get("data", {}).get("token")
            )  # Note: login views shows 'token' in data_dict
            return email, auth_token
        else:
            resp.failure(f"Setup: Login failed: {resp.text}")
            return None, None
