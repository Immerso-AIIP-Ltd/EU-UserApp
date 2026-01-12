import random
import string

from locust import HttpUser, between, task


class LogoutUser(HttpUser):
    wait_time = between(1, 5)
    auth_token = None
    device_id = None

    def on_start(self) -> None:
        self.device_id = "loadtest-device-" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10),
        )
        self.headers = {
            "Content-Type": "application/json",
            "x-device-id": self.device_id,
            "api_client": "android_app",
            "x-platform": "android",
            "x-app-version": "1.0.0",
            "x-country": "IN",
            "x-api-client": "android_app",
        }
        # Create user and login to get token
        from loadtests.common.auth import register_and_login

        email, auth_token = register_and_login(self.client, self.headers)

        if auth_token:
            self.auth_token = auth_token
            self.headers["x-api-token"] = self.auth_token
        else:
            pass

    @task(1)
    def logout_user(self) -> None:
        if not self.auth_token:
            return

        with self.client.post(
            "/user/v1/user/logout",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                self.auth_token = None  # Clear token
            else:
                response.failure(f"Logout failed: {response.text}")

            # Stop user after logout as they have no token
            self.stop()

    # Note: Deactivate also requires token. If we run logout, we can't run deactivate.
    # In a real scenario we might weigh them or have different User classes.
    # For now, we just test logout. To test deactivate, we would need another class or logic.
