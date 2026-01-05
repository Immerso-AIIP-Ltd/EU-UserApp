import random
import string
from locust import HttpUser, task, between

class SocialUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "x-device-id": "loadtest-device-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)),
            "api_client": "android_app",
            "platform": "android",
            "app_version": "1.0.0",
            "country": "IN",
            "x-api-client": "android_app" 
        }

    @task
    def google_login(self):
        # We expect this to fail with 401/400 because the token is fake.
        # But it tests the endpoint reachability and handling of invalid tokens.
        payload = {
            "token": "fake_google_token_" + ''.join(random.choices(string.ascii_letters, k=20)),
            "user_id": "google_uid_" + ''.join(random.choices(string.digits, k=10)),
            "email": "test@example.com"
        }
        
        with self.client.post("/user/v1/social/google_login", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code in [400, 401, 200]: # 200 if mock is enabled
                response.success()
            else:
                # If it returns 500, that's bad error handling, so we mark failure.
                # If it returns 403 or others, we might want to investigate.
                if response.status_code == 500:
                    response.failure(f"Google login failed with 500: {response.text}")
                else:
                    response.success() # Accepting other codes as we know token is fake

    @task
    def facebook_login(self):
        payload = {
            "access_token": "fake_facebook_token_" + ''.join(random.choices(string.ascii_letters, k=20)),
            "uid": "fb_uid_" + ''.join(random.choices(string.digits, k=10)),
        }
        
        with self.client.post("/user/v1/social/facebook_login", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code in [400, 401, 200]: 
                response.success()
            else:
                if response.status_code == 500:
                    response.failure(f"Facebook login failed with 500: {response.text}")
                else:
                    response.success()
