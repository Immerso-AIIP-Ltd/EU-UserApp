# This file is the main entry point for Locust, collecting all user types.
# It also triggers the bootstrap process to fetch initial data.

# Import user classes to be included in the test
from loadtests.users.register import RegisterUser
from loadtests.users.login import LoginUser
from loadtests.users.logout import LogoutUser
from loadtests.users.profile import ProfileUser
from loadtests.users.social import SocialUser
from loadtests.users.waitlist import WaitlistUser
from loadtests.users.device import DeviceUser

# Import and register the bootstrap function
from loadtests.common.bootstrap import bootstrap_all

# To run the tests, use the following command:
# locust -f loadtests/locustfile.py

from locust import HttpUser, task

class SanityUser(HttpUser):
    weight = 1

    @task
    def ping(self):
        self.client.get("/user/v1/internal/monitoring/health")
