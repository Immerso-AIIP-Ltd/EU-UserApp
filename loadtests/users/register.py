import random
import string

from locust import between, task

from loadtests.common.base_user import EncryptedUser


class RegistrationUser(EncryptedUser):
    """User that performs registration tasks."""

    wait_time = between(1, 5)

    def generate_random_email(self) -> str:
        """Generate a random email for load testing."""
        random_str = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10),
        )
        return f"loadtest_{random_str}@example.com"

    @task
    def register_step1_only(self) -> None:
        """Only hits register_with_profile as requested."""
        email = self.generate_random_email()
        password = "Password123!"  # noqa: S105

        payload = {"email": email, "password": password, "calling_code": "+1"}

        with self.post_encrypted(
            "/user/v1/register/register_with_profile",
            payload,
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Register Step 1 failed: {response.text}")
            else:
                response.success()
