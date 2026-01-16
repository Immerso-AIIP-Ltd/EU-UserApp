import random
import string

from locust import between, task

from loadtests.common.authenticated_user import AuthenticatedUser


class ProfileUser(AuthenticatedUser):
    """User that performs profile-related tasks."""

    wait_time = between(1, 5)

    @task(3)
    def get_profile(self) -> None:
        """Fetch the user's profile."""
        if not self.auth_token:
            return
        # GET /profile uses headers
        with self.client.get(
            "/user/v1/auth/user_profile/profile",
            headers=self.client.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Get Profile failed: {resp.text}")

    @task(1)
    def update_profile(self) -> None:
        """Update the user's profile."""
        if not self.auth_token:
            return

        # PUT /profile expects UpdateProfileRequest (NOT Encrypted)
        payload = {
            "name": f"Updated Name {random.randint(1, 1000)}",  # noqa: S311
            "gender": random.choice(["M", "F", "O"]),  # noqa: S311
            "about_me": "Load Testing...",
            "country": "US",
            # Removing birth_date temporarily to debug overflow issue
            # "birth_date": "1995-05-05"
        }

        with self.client.put(
            "/user/v1/auth/user_profile/profile",
            json=payload,
            headers=self.client.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Update Profile failed: {resp.text}")

    @task(1)
    def update_email_mobile_flow(self) -> None:
        """Update the user's email/mobile."""
        if not self.auth_token:
            return

        # POST /update_email_mobile expects UpdateEmailMobileRequest (NOT Encrypted)
        random_str = "".join(random.choices(string.ascii_lowercase, k=8))  # noqa: S311
        new_email = f"loadtest_updated_{random_str}@example.com"
        payload = {
            "email": new_email,
            # Removed calling_code as it conflicts with email per schema validation
        }

        with self.client.post(
            "/user/v1/auth/user_profile/update_email_mobile",
            json=payload,
            headers=self.client.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                # Returns redirect URL for OTP verification
                resp.success()
            else:
                resp.failure(f"Update Email failed: {resp.text}")
                return

        # Removed verification step as verify_otp_register is removed from load test
