import logging
import os
import random
import string
from typing import Any

from locust import HttpUser

from loadtests.common.encryption import encrypt_payload

# Get OTP bypass secret from env or use default
OTP_BYPASS_SECRET = os.getenv(
    "APP_LOAD_TEST_BYPASS_SECRET",
    "LOAD_TEST_BYPASS_SECRET_123",
)


class EncryptedUser(HttpUser):
    """
    Base user that encrypts JSON payloads before sending.

    Also injects OTP bypass headers.
    """

    abstract = True

    def on_start(self) -> None:
        """Called when a User is started."""
        random_str = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10),  # noqa: S311
        )
        self.device_id = f"loadtest-device-{random_str}"
        # Initialize session headers with required fields
        self.client.headers.update(
            {
                "x-load-test-bypass": OTP_BYPASS_SECRET,
                "Content-Type": "application/json",
                "x-api-client": "android_app",
                "x-device-id": self.device_id,
                "x-platform": "android",
                "x-country": "US",
                "x-app-version": "1.0.0",
            },
        )

    def post_encrypted(
        self, endpoint: str, json_payload: dict[str, Any], **kwargs: Any,
    ) -> Any:
        """Helper to encrypt payload and send POST request."""
        try:
            encrypted_data = encrypt_payload(json_payload)
            return self.client.post(endpoint, json=encrypted_data, **kwargs)
        except Exception as e:
            logging.error(f"Encryption failed for {endpoint}: {e}")
            raise e

    def put_encrypted(
        self, endpoint: str, json_payload: dict[str, Any], **kwargs: Any,
    ) -> Any:
        """Helper to encrypt payload and send PUT request."""
        try:
            encrypted_data = encrypt_payload(json_payload)
            return self.client.put(endpoint, json=encrypted_data, **kwargs)
        except Exception as e:
            logging.error(f"Encryption failed for {endpoint}: {e}")
            raise e
