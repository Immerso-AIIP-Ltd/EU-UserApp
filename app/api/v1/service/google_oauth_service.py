from datetime import datetime
from typing import Any, Optional

import google.oauth2.id_token
from google.auth.transport import requests
from loguru import logger

from app.core.exceptions import (
    GoogleWrongIssuer,
    InvalidSocialToken,
    InvalidSocialUID,
)
from app.settings import settings


class GoogleOAuthService:
    """Service to handle Google OAuth verification."""

    NAME = "google"

    def __init__(self, id_token: str, platform: str):
        self.id_token = id_token
        self.platform = platform
        self.uid = None
        self.name = None
        self.email = None
        self.expiry: Optional[datetime] = None

    async def verify_id_token(self, uid: str) -> Any:
        """Verify the Google ID token."""
        try:
            if self.platform == "ios":
                google_client_id = settings.google_ios_client_id
            elif self.platform == "android":
                google_client_id = settings.google_android_client_id
            else:
                google_client_id = settings.google_client_id

            # In a real async environment, we might want to run this in a thread pool
            # since verify_oauth2_token is blocking, but for now we'll keep it simple.
            id_info = google.oauth2.id_token.verify_oauth2_token(
                self.id_token,
                requests.Request(),
                google_client_id,
            )

            logger.info(f"GOOGLE VERIFY TOKEN response: {id_info}")

            if id_info["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise GoogleWrongIssuer()

            if id_info["sub"] != uid:
                raise InvalidSocialUID()

            self.uid = id_info["sub"]
            self.name = id_info.get("name")
            self.email = id_info.get("email")
            self.expiry = datetime.utcfromtimestamp(int(id_info["exp"]))

        except ValueError as e:
            logger.error(f"Google Token Verification Error: {e!s}")
            raise InvalidSocialToken()
        except Exception as e:
            logger.exception(f"Unexpected error during Google verification: {e!s}")
            raise InvalidSocialToken()

    async def get_email(self) -> Any:
        return self.email

    async def get_name(self) -> Any:
        return self.name

    async def get_uid(self) -> Any:
        return self.uid

    async def get_token(self) -> Any:
        return self.id_token

    async def get_expiry(self) -> Any:
        return self.expiry
