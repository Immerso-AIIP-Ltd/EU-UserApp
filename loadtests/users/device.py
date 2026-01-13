import random
import string

from locust import between, task

from loadtests.common.base_user import EncryptedUser


class DeviceUser(EncryptedUser):
    """User that performs device-related tasks."""

    wait_time = between(1, 5)

    def on_start(self) -> None:
        """Run on user start."""
        super().on_start()
        random_str = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10),
        )
        self.device_id = f"loadtest-device-{random_str}"
        self.client.headers.update(
            {
                "x-device-id": self.device_id,
                "api_client": "android_app",
                "x-platform": "android",
                "x-app-version": "1.0.0",
                "x-country": "IN",
                "x-api-client": "android_app",
            },
        )

    @task
    def check_device_invite(self) -> None:
        """Check if the device has an invite."""
        # GET request, usually not encrypted body
        with self.client.get(
            f"/user/v1/device/{self.device_id}",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                # 404 means not found/active, which is valid for random device
                response.success()
            else:
                response.failure(
                    f"Check device invite failed: {response.status_code} - {response.text}",
                )

    @task
    def invite_device(self) -> None:
        """Identify device with a fake coupon."""
        # POST request with encryption
        random_digits = "".join(random.choices(string.digits, k=5))
        payload = {
            "device_id": self.device_id,
            "coupon_id": f"fake_coupon_{random_digits}",
        }
        # Expecting 404 or 400 for fake coupon
        with self.post_encrypted(
            "/user/v1/device/invite",
            payload,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400, 404]:
                response.success()
            elif response.status_code != 200:
                response.failure(f"Invite device failed: {response.text}")

    @task
    def register_device(self) -> None:
        """Register the device via the API."""
        # POST request with encryption
        # This endpoint might just take device_id in body or header?
        # User list says: POST /user/v1/device/register
        # Let's assume it takes device_id, platform, etc.
        payload = {
            "device_id": self.device_id,
            "platform": "android",
            "device_token": "dummy_fcm_token",
        }
        with self.post_encrypted(
            "/user/v1/device/register",
            payload,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 409]:
                response.success()
            else:
                response.failure(f"Register device failed: {response.text}")
