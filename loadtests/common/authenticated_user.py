import random
import string

from loadtests.common.base_user import EncryptedUser


class AuthenticatedUser(EncryptedUser):
    """User that registers and logs in on start to get an auth token."""

    abstract = True
    auth_token = None
    email = None
    password = "Password123!"  # noqa: S105

    def on_start(self) -> None:
        """Run on user start."""
        super().on_start()
        self.perform_registration_and_login()

    def perform_registration_and_login(self) -> None:
        """Register and login user to get auth token."""
        random_str = "".join(random.choices(string.ascii_lowercase, k=10))  # noqa: S311
        self.email = f"loadtest_auth_{random_str}@example.com"

        # 1. Register Device (Required for Session creation)
        # We do this FIRST to ensure DB integrity for later steps
        payload_device = {
            "device_id": self.device_id,
            "device_name": "LoadTest Device",
            "device_type": "mobile",
            "platform": "android",
            "push_token": "fake_push_token",
        }
        with self.post_encrypted(
            "/user/v1/device/device_registration",
            payload_device,
            catch_response=True,
        ) as resp:
            if resp.status_code not in [200, 409]:
                resp.failure(f"Setup: Device registration failed: {resp.text}")
                return

        # 2. Register
        payload_reg = {
            "email": self.email,
            "password": self.password,
            "calling_code": "+1",
        }
        with self.post_encrypted(
            "/user/v1/register/register_with_profile",
            payload_reg,
            catch_response=True,
        ) as resp:
            if resp.status_code not in [200, 409]:
                resp.failure(f"Setup: Register failed: {resp.text}")
                return

        # 3. Verify OTP
        payload_verify = {
            "email": self.email,
            "otp": "123456",
            "intent": "registration",
            "calling_code": "+1",
        }
        with self.post_encrypted(
            "/user/v1/register/verify_otp_register",
            payload_verify,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                # Prefer accessToken as per new API, fallback to token
                self.auth_token = data.get("accessToken") or data.get("token")
                if self.auth_token:
                    self.client.headers.update({"x-api-token": self.auth_token})
                else:
                    resp.failure("Setup: Token missing in verify response")
            else:
                resp.failure(f"Setup: Verify OTP failed: {resp.text}")
