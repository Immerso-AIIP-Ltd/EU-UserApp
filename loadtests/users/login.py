import random
import string
from locust import HttpUser, task, between


class LoginUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "x-device-id": "loadtest-device-"
            + "".join(random.choices(string.ascii_lowercase + string.digits, k=10)),
            "api_client": "android_app",
            "platform": "android",
            "app_version": "1.0.0",
            "country": "IN",
            "x-api-client": "android_app",
        }
        # Ideally we should have a pool of users.
        # For now, we assume some pre-seeded users or just test with failure/random credentials to stress the DB lookups.

    @task
    def login_user(self):
        # Using random credentials to stress test auth failure paths if no seeded data
        email = f"loadtest_{''.join(random.choices(string.ascii_lowercase, k=5))}@example.com"
        password = "Password123!"

        payload = {"email": email, "password": password, "login_type": "email"}

        # We expect 400/404/401 mostly if users don't exist, but that's still load.
        # If we want successful login, we need to register first in on_start or use a known user.
        with self.client.post(
            "/user/v1/user/login",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            # Just recording the response, not marking failure on 4xx as that might be expected without seeded data
            if response.status_code in [200, 400, 401, 404]:
                response.success()
            else:
                response.failure(
                    f"Login unexpected error: {response.status_code} - {response.text}"
                )

            if response.status_code == 200:
                self.auth_token = response.json().get("data", {}).get("auth_token")

    @task
    def forgot_password(self):
        email = f"loadtest_{''.join(random.choices(string.ascii_lowercase, k=5))}@example.com"
        payload = {"email": email}
        with self.client.post(
            "/user/v1/user/forgot_password",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 404]:
                response.success()
            else:
                response.failure(f"Forgot password failed: {response.text}")
