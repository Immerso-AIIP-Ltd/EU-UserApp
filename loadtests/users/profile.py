import random
import string
from locust import HttpUser, task, between


class ProfileUser(HttpUser):
    wait_time = between(1, 5)
    auth_token = None

    def on_start(self):
        self.device_id = "loadtest-device-" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10)
        )
        self.headers = {
            "Content-Type": "application/json",
            "x-device-id": self.device_id,
            "api_client": "android_app",
            "platform": "android",
            "app_version": "1.0.0",
            "country": "IN",
            "x-api-client": "android_app",
        }
        # Create user and login to get token
        email = f"loadtest_{''.join(random.choices(string.ascii_lowercase, k=10))}@example.com"
        password = "Password123!"

        # 1. Register
        reg_payload = {
            "email": email,
            "password": password,
            "name": "Profile Test User",
            "birth_date": "1990-01-01",
            "gender": "male",
        }
        with self.client.post(
            "/user/v1/register/register_with_profile",
            json=reg_payload,
            headers=self.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                print(f"Profile setup failed: Register {resp.text}")
                return

        # 2. Login
        login_payload = {"email": email, "password": password, "login_type": "email"}
        with self.client.post(
            "/user/v1/user/login",
            json=login_payload,
            headers=self.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                self.auth_token = resp.json().get("data", {}).get("auth_token")
                self.headers["x-api-token"] = self.auth_token
            else:
                print(f"Profile setup failed: Login {resp.text}")

    @task(3)
    def get_profile(self):
        if not self.auth_token:
            return
        with self.client.get(
            "/user/v1/user_profile/profile", headers=self.headers, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get profile failed: {response.text}")

    @task(1)
    def update_profile(self):
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
