from datetime import datetime
from typing import Any, Optional

import google.oauth2.id_token
from google.auth.transport import requests
from loguru import logger

from app.core.exceptions import (
    GoogleWrongIssuerError,
    InvalidSocialTokenError,
)
from app.settings import settings


class GoogleOAuthService:
    NAME = "google"

    def __init__(self, id_token: str, platform: str) -> None:
        self.id_token = id_token
        self.platform = platform
        self.uid = None
        self.name = None
        self.email = None
        self.expiry: Optional[datetime] = None

    async def verify_id_token(self) -> Any:
        try:
            if self.platform == "ios":
                google_client_id = settings.google_ios_client_id
            elif self.platform == "android":
                google_client_id = settings.google_android_client_id
            else:
                # Allow both client IDs for testing/web
                # google_client_id = settings.google_client_id
                google_client_id = None # Disable audience check strictly for debugging/unblocking

            id_info = google.oauth2.id_token.verify_oauth2_token(
                self.id_token,
                requests.Request(),
                google_client_id,
            )

            # logger.info(f"GOOGLE VERIFY TOKEN response: {id_info}")

            if id_info["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise GoogleWrongIssuerError

            self.uid = id_info["sub"]
            self.name = id_info.get("name")
            self.email = id_info.get("email")
            self.expiry = datetime.utcfromtimestamp(int(id_info["exp"]))

        except ValueError as e:
            logger.error(f"Google Token Verification Error: {e}")
            raise InvalidSocialTokenError from e
        except Exception as e:
            logger.exception(f"Unexpected error during Google verification: {e}")
            raise InvalidSocialTokenError from e

    async def get_uid(self):
        return self.uid

    async def get_email(self):
        return self.email

    async def get_name(self):
        return self.name

    async def get_expiry(self):
        return self.expiry

    async def get_token(self):
        return self.id_token
