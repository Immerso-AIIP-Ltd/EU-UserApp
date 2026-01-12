import random
import string

from locust import HttpUser, between, task


class ProfileUser(HttpUser):
    wait_time = between(1, 5)
    auth_token = None

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

    @task(3)
    def get_profile(self) -> None:
        if not self.auth_token:
            return
        with self.client.get(
            "/user/v1/user_profile/profile",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get profile failed: {response.text}")

    @task(1)
    def update_profile(self) -> None:
        if not self.auth_token:
            return

        payload = {
            "name": f"Updated Name {random.randint(1, 100)}",
            "gender": "female",
            "about_me": "I am a load test user",
            "country": "US",
        }

        with self.client.put(
            "/user/v1/user_profile/profile",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Update profile failed: {response.text}")
