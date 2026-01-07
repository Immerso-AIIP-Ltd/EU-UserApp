import random
import string
from locust import HttpUser, task, between


class LoginUser(HttpUser):
    host = "http://localhost:8880"
    weight = 1
    wait_time = between(1, 5)

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "x-device-id": "loadtest-device-"
            + "".join(random.choices(string.ascii_lowercase + string.digits, k=10)),
            "x-platform": "android",
            "x-app-version": "1.0.0",
            "x-country": "IN",
            "x-api-client": "android_app",
        }
        self.auth_token = None

    @task(2)
    def login_user(self):
        email = f"loadtest_{''.join(random.choices(string.ascii_lowercase, k=5))}@example.com"
        password = "Password123!"

        payload = {
            "email": email,
            "password": password,
            "login_type": "email",
        }

        with self.client.post(
            "/user/v1/user/login",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                self.auth_token = response.json().get("data", {}).get("auth_token")
                response.success()
            elif response.status_code in [400, 401, 404]:
                response.success()
            else:
                response.failure(
                    f"Login error: {response.status_code} - {response.text}"
                )

    @task(1)
    def change_password(self):
        """
        Calls change_password ONLY if login was successful
        """
        if not self.auth_token:
            return  # skip until logged in

        new_password = "NewPassword123!"

        payload = {
            "new_password": new_password,
            "new_password_confirm": new_password,
        }

        headers = {
            **self.headers,
            "x-api-token": self.auth_token,
        }

        with self.client.put(
            "/user/v1/user/change_password",
            json=payload,
            headers=headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [400, 401]:
                response.success()  # expected in some cases
            else:
                response.failure(
                    f"Change password failed: {response.status_code} - {response.text}"
                )

    @task(1)
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
                response.failure(
                    f"Forgot password failed: {response.status_code} - {response.text}"
                )
