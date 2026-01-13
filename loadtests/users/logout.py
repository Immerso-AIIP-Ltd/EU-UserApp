from locust import between, task

from loadtests.common.authenticated_user import AuthenticatedUser


class LogoutUser(AuthenticatedUser):
    """User that performs logout-related tasks."""

    wait_time = between(1, 5)

    @task(3)
    def logout_flow(self) -> None:
        """Perform the user logout flow."""
        if not self.auth_token:
            return

        with self.client.post(
            "/user/v1/auth/user/logout",
            headers=self.client.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
                self.auth_token = None
            else:
                resp.failure(f"Logout failed: {resp.text}")

        # Stop after logout
        self.stop()

    @task(1)
    def deactivate_flow(self) -> None:
        """Perform the user deactivation flow."""
        # Only if we have a token
        if not self.auth_token:
            return

        with self.client.post(
            "/user/v1/auth/user/deactivate",
            headers=self.client.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
                self.auth_token = None
            else:
                resp.failure(f"Deactivate failed: {resp.text}")

        self.stop()
