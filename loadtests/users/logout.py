import random
import string
from locust import HttpUser, task, between


class LogoutUser(HttpUser):
    wait_time = between(1, 5)
    auth_token = None
    device_id = None

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
            "name": "Logout Test User",
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
                print(f"Components setup failed: Register {resp.text}")
                return  # Stop here if setup fails

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
                print(f"Components setup failed: Login {resp.text}")

    @task(1)
    def logout_user(self):
        if not self.auth_token:
            return

        with self.client.post(
            "/user/v1/user/logout", headers=self.headers, catch_response=True
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
