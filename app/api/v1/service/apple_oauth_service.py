from datetime import datetime
from typing import Any, Dict, List, Optional

import jwt
import requests
from jwt import PyJWKClient
from loguru import logger

from app.core.constants import (
    AppleLogMessages,
    AuthConfig,
    JwtOptions,
    PlatformTypes,
    RequestParams,
    SocialProviders,
)
from app.core.exceptions import (
    AppleKeyFetchError,
    InvalidSocialTokenError,
    InvalidSocialUIDError,
)
from app.settings import settings


class AppleOAuthService:
    """Service to handle Apple OAuth verification."""

    NAME = SocialProviders.APPLE

    def __init__(self, id_token: str, platform: str) -> None:
        self.id_token = id_token
        self.platform = platform
        self.uid: Optional[str] = None
        self.email: Optional[str] = None
        self.expiry: Optional[datetime] = None

    async def get_client_id(self) -> str:
        """Retrieve the correct Apple client ID based on platform."""
        if self.platform == PlatformTypes.IOS:
            return settings.apple_ios_client_id
        return settings.apple_client_id

    async def _get_apple_public_keys(self) -> List[Dict[str, Any]]:
        """Fetch Apple's public keys."""
        # In a real production environment, checking Redis first would be better.
        # But for this implementation we will fetch directly for simplicity.
        # If Redis was strictly required for keys, we would inject it.
        try:
            response = requests.get(settings.apple_public_key_url, timeout=10)
            response.raise_for_status()
            return response.json().get("keys", [])
        except Exception as e:
            logger.error(AppleLogMessages.FETCH_KEYS_FAILED.format(e))
            raise AppleKeyFetchError from e

    async def _get_key_by_kid(
        self,
        keys: List[Dict[str, Any]],
        kid: str,
    ) -> Optional[Dict[str, Any]]:
        for key in keys:
            if key.get(RequestParams.KID) == kid:
                return key
        return None

    async def verify_id_token(self, uid: str) -> Any:
        """Verify the Apple ID Token."""

        try:
            jwk_client = PyJWKClient(settings.apple_public_key_url)
            signing_key = jwk_client.get_signing_key_from_jwt(self.id_token)

            decoded = jwt.decode(
                self.id_token,
                signing_key.key,
                algorithms=[AuthConfig.RS256],
                audience=await self.get_client_id(),
                issuer=settings.apple_issuer,
                options={JwtOptions.VERIFY_EXP: True},
            )
            exp_raw: Optional[Any] = decoded.get("exp")
            if decoded.get("sub") != uid:
                raise InvalidSocialUIDError

            self.uid = decoded.get("sub")
            self.email = decoded.get(RequestParams.EMAIL)
            if exp_raw is not None:
                self.expiry = datetime.utcfromtimestamp(float(exp_raw))
            else:
                self.expiry = None

        except jwt.ExpiredSignatureError as e:
            logger.error(AppleLogMessages.ID_TOKEN_EXPIRED)
            raise InvalidSocialTokenError from e

        except jwt.InvalidTokenError as e:
            logger.error(AppleLogMessages.INVALID_TOKEN.format(e))
            raise InvalidSocialTokenError from e

        except Exception as e:
            logger.exception(AppleLogMessages.UNEXPECTED_ERROR.format(e))
            raise InvalidSocialTokenError from e

    async def get_email(self) -> Optional[str]:
        """Get the user's email."""
        return self.email

    async def get_name(self) -> Optional[str]:
        """Get the user's name (placeholder for Apple's separate name object)."""
        # Apple ID token does not contain name.
        # Name is sent only on first login in a separate JSON object.
        # Since our schema doesn't capture it currenty, we return None.
        return None

    async def get_uid(self) -> Optional[str]:
        """Get the user's UID."""
        return self.uid

    async def get_token(self) -> str:
        """Get the ID token."""
        return self.id_token

    async def get_expiry(self) -> Optional[datetime]:
        """Get the token expiry."""
        return self.expiry
