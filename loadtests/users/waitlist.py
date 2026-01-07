import random
import string
from locust import HttpUser, task, between


class WaitlistUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """
        Setup initial headers for each user session.
        """
        self.device_id = "loadtest-device-" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10)
        )
        self.headers = {
            "Content-Type": "application/json",
            "x-device-id": self.device_id,
            "x-api-client": "android_app",
            "x-platform": "android",
            "x-app-version": "1.0.0",
            "x-country": "IN",
        }
        self.email = None
        self.is_verified = False

    @task(3)
    def join_waitlist(self):
        """
        Scenario: User joins the waitlist.
        """
        self.email = f"waitlist_{''.join(random.choices(string.ascii_lowercase, k=10))}@example.com"
        payload = {
            "device_id": self.device_id,
            "email_id": self.email,
            "name": "LoadTest User",
        }

        with self.client.post(
            "/user/v1/waitlist", json=payload, headers=self.headers, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"Join waitlist failed: {response.status_code} - {response.text}"
                )

    @task(1)
    def resend_otp(self):
        """
        Scenario: User requests to resend OTP for waitlist.
        """
        if not self.email:
            return

        payload = {
            "email_id": self.email,
        }

        with self.client.post(
            "/user/v1/waitlist_resend_otp",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"Resend OTP failed: {response.status_code} - {response.text}"
                )

    @task(2)
    def friend_invite(self):
        """
        Scenario: User invites friends (Requires having joined waitlist).
        """
        if not self.email:
            return

        # Invite 2 friends
        friends = [
            f"friend_{''.join(random.choices(string.ascii_lowercase, k=5))}@example.com",
            f"friend_{''.join(random.choices(string.ascii_lowercase, k=5))}@example.com",
        ]

        payload = {"invited_list": friends}

        # The API requires x-device-id in headers (already in self.headers)
        with self.client.post(
            "/user/v1/friend_invite",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"Friend invite failed: {response.status_code} - {response.text}"
                )
