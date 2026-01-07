import random
import string
from locust import HttpUser, task, between


class DeviceUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        self.device_id = "loadtest-device-" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10)
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

    @task
    def check_device_invite(self):
        # This checks the current device ID status
        with self.client.get(
            f"/user/v1/device/{self.device_id}",
            headers=self.headers,
            catch_response=True,
        ) as response:
            # 200 if invited, 400/404 if not. Both are valid from load perspective.
            if response.status_code in [200, 400, 404]:
                response.success()
            else:
                response.failure(
                    f"Check device invite failed: {response.status_code} - {response.text}"
                )

    @task
    def invite_device(self):
        # We need a valid coupon_id to test this properly.
        # With a fake coupon, we expect 400.
        payload = {
            "device_id": self.device_id,
            "coupon_id": "fake_coupon_" + "".join(random.choices(string.digits, k=5)),
        }

        with self.client.post(
            "/user/v1/device/invite",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 404, 422]:
                response.success()
            else:
                response.failure(
                    f"Invite device failed: {response.status_code} - {response.text}"
                )
