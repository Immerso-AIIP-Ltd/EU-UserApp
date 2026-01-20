import random
import string

from locust import between, task

from loadtests.common.base_user import EncryptedUser


class LoginUser(EncryptedUser):
    """User that performs login-related tasks."""

    wait_time = between(1, 5)

    email = None
    password = "Password123!"  # noqa: S105
    auth_token = None
    refresh_token = None

    def on_start(self) -> None:
        """Run on user start to register a fresh user."""
        super().on_start()
        # Register a fresh user for this session
        random_id = "".join(random.choices(string.ascii_lowercase, k=10))  # noqa: S311
        self.email = f"loadtest_{random_id}@example.com"

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
                resp.failure(f"Setup login user device failed: {resp.text}")
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
                resp.failure(f"Setup login user register failed: {resp.text}")
                return

        # 3. Verify OTP (Required for token)
        # We hit this ONLY ONCE per user start
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
                self.refresh_token = data.get("refreshToken") or data.get(
                    "refresh_token",
                )
                if self.auth_token:
                    self.client.headers.update({"x-api-token": self.auth_token})
            else:
                resp.failure(f"Setup login user verify failed: {resp.text}")

    @task(3)
    def login(self) -> None:
        """Perform user login via the API."""
        payload = {"email": self.email, "password": self.password}
        with self.post_encrypted(
            "/user/v1/user/login",
            payload,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                # Prefer accessToken as per new API, fallback to auth_token
                self.auth_token = data.get("accessToken") or data.get("auth_token")
                if self.auth_token:
                    self.client.headers.update({"x-api-token": self.auth_token})
                resp.success()
            else:
                resp.failure(f"Login failed: {resp.text}")

    @task(1)
    def forgot_password_init_only(self) -> None:
        """Initialize the forgot password flow."""
        # Only hit the init endpoint to avoid verify_otp_register as requested
        payload = {"email": self.email, "calling_code": "+1"}
        self.post_encrypted("/user/v1/user/forgot_password", payload)

    @task(1)
    def change_password(self) -> None:
        """Change the user's password."""
        # Change password requires auth
        if self.auth_token:
            new_pass = "NewPassword123!"  # noqa: S105
            payload = {"new_password": new_pass, "new_password_confirm": new_pass}
            # change_password endpoint expects plain JSON
            with self.client.put(
                "/user/v1/user/change_password",
                json=payload,
                catch_response=True,
            ) as resp:
                if resp.status_code == 200:
                    self.password = new_pass  # Update local state
                else:
                    resp.failure(f"Change Password failed: {resp.text}")

    @task(1)
    def logout_and_deactivate(self) -> None:
        """Logout and stop the user session."""
        # If we logout, we lose the token. Steps might fail after.
        # So we should be careful. Maybe do this last or re-login.
        if self.auth_token:
            self.client.post("/user/v1/auth/user/logout")
            # Clear header
            self.client.headers.pop("x-api-token", None)
            self.auth_token = None

            # Re-login to continue testing?
            # Or just stop this iteration.
            self.stop()  # Stop this user
