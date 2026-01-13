import random
import string

from locust import between, task

from loadtests.common.authenticated_user import AuthenticatedUser


class WaitlistUser(AuthenticatedUser):
    """User that performs waitlist tasks."""

    wait_time = between(1, 5)
    joined = False

    def on_start(self) -> None:
        """Run on user start."""
        super().on_start()

    @task(3)
    def join_waitlist_only(self) -> None:
        """Only hits join_waitlist to avoid OTP verify/resend APIs from tasks."""
        if self.joined:
            return

        payload = {
            "device_id": self.device_id,
            "email_id": self.email,
            "name": "LoadTest User",
        }

        with self.post_encrypted(
            "/user/v1/auth/social/waitlist",
            payload,
            catch_response=True,
        ) as resp:
            if resp.status_code in [200, 409]:
                # We mark as joined even if not verified just to move on in load test tasks
                self.joined = True
                resp.success()
            else:
                resp.failure(f"Join Waitlist failed: {resp.text}")

    @task(2)
    def friend_invite(self) -> None:
        """Send a friend invite."""
        if not self.joined:
            return

        random_str = "".join(random.choices(string.ascii_lowercase, k=5))
        friends = [
            {
                "email": f"friend_{random_str}@example.com",
            },
        ]
        payload = {"invited_list": friends}

        with self.client.post(
            "/user/v1/auth/social/friend_invite",
            json=payload,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                error_msg = f"Friend Invite failed: {resp.status_code} - {resp.text}"
                resp.failure(error_msg)
            else:
                resp.success()
