from locust import between, task

from loadtests.common.base_user import EncryptedUser


class SocialUser(EncryptedUser):
    """User that performs social login tasks."""

    wait_time = between(1, 5)

    # Needs valid ID tokens to work.
    # Placeholder for now.

    @task
    def google_login(self) -> None:
        """Attempt Google login (placeholder)."""
        # This will fail without a valid ID token signed by Google
        # payload = {"id_token": "dummy_token_123", "uid": "123"}
        # self.post_encrypted("/user/v1/social/google_login", payload)
