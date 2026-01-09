import random
import string
import logging
from locust import HttpUser, task, between


class RegisterUser(HttpUser):
    host = "http://localhost:8880"
    wait_time = between(1, 5)

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "x-device-id": "loadtest-device-"
            + "".join(random.choices(string.ascii_lowercase + string.digits, k=10)),
            "api_client": "android_app",
            "x-platform": "android",
            "x-app-version": "1.0.0",
            "x-country": "IN",
            "x-api-client": "android_app",
        }
        self.email = None

    @task(1)
    def register_with_profile(self):
        email = f"loadtest_{''.join(random.choices(string.ascii_lowercase, k=10))}@example.com"
        password = "Password123!"

        payload = {
            "email": email,
            "password": password,
            "name": "Load Test User",
            "birth_date": "1990-01-01",
            "gender": "male",
        }

        with self.client.post(
            "/user/v1/register/register_with_profile",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                # Store email/password for verify step if we implement it,
                # or for other tasks if this was a sequential task set
                self.email = email
            else:
                response.failure(f"Registration failed: {response.text}")

    @task(1)
    def resend_otp(self):
        """
        Load test OTP resend (rate limiting, Redis, validation)
        """
        if not self.email:
            return

        payload = {
            "email": self.email,
            "intent": "registration",
        }

        with self.client.post(
            "/user/v1/register/resend_otp",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400]:
                response.success()
            else:
                response.failure(
                    f"Resend OTP failed: {response.status_code} - {response.text}"
                )
