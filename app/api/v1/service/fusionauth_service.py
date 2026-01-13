from typing import Any, Dict, List, Optional

import jwt
from fusionauth.fusionauth_client import FusionAuthClient
from jwt import PyJWKClient

from app.core.constants import CacheTTL, ErrorMessages, HTTPStatus
from app.core.exceptions.exceptions import FusionAuthError
from app.settings import settings

# Global cache for JWKS
_jwks_client = None


class FusionAuthService:
    """Service to interact with FusionAuth API."""

    @staticmethod
    def get_jwks_url() -> str:
        """Get the JWKS URL."""
        return f"{settings.fusionauth_url}/.well-known/jwks.json"

    @staticmethod
    def get_client() -> FusionAuthClient:
        """Get the FusionAuth client."""
        return FusionAuthClient(settings.fusionauth_api_key, settings.fusionauth_url)

    @classmethod
    def get_jwks_client(cls) -> PyJWKClient:
        """Get the JWKS client (cached global)."""
        global _jwks_client  # noqa: PLW0603
        if _jwks_client is None:
            _jwks_client = PyJWKClient(cls.get_jwks_url())
        return _jwks_client

    @classmethod
    def verify_token(cls, token: str) -> Dict[str, Any]:
        """Verify the JWT token using FusionAuth JWKS."""
        try:
            jwks_client = cls.get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.fusionauth_client_id,
            )
        except Exception as e:
            raise FusionAuthError(
                http_code=HTTPStatus.UNAUTHORIZED,
                detail=ErrorMessages.FUSION_AUTH_VALIDATION_ERROR,
            ) from e

    @classmethod
    def create_fusion_user(cls, user_uuid: str, email: Optional[str] = None) -> str:
        """
        Creates a user in FusionAuth with the local user_uuid as the FusionAuth User ID.

        If email is provided, it is set. If not, the user_uuid is used as the username.
        """
        client = cls.get_client()

        user_body: Dict[str, Any] = {"password": None}  # No password in FA
        if email:
            user_body["email"] = email
        else:
            user_body["username"] = user_uuid

        user_request = {
            "user": user_body,
            "registration": {"applicationId": settings.fusionauth_client_id},
            "skipVerification": True,
        }

        # Check if user exists by ID first
        search_response = client.retrieve_user(user_uuid)
        if search_response.was_successful():
            user = search_response.success_response["user"]
            registrations = user.get("registrations", [])
            is_registered = any(
                r["applicationId"] == settings.fusionauth_client_id
                for r in registrations
            )

            if not is_registered:
                # Use keyword args for safety
                reg_response = client.register(
                    user_id=user_uuid,
                    request={
                        "registration": {
                            "applicationId": settings.fusionauth_client_id,
                        },
                    },
                )
                if not reg_response.was_successful():
                    raise FusionAuthError(
                        http_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                        detail=ErrorMessages.FUSION_AUTH_REGISTRATION_ERROR,
                    )

            return user_uuid

        # Create new user
        # Use keyword args for safety
        response = client.register(user_id=user_uuid, request=user_request)

        if response.was_successful():
            return response.success_response["user"]["id"]

        raise FusionAuthError(
            http_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.FUSION_AUTH_SYNC_ERROR,
        )

    @classmethod
    def issue_token(
        cls,
        fusion_user_id: str,
        roles: Optional[List[str]] = None,
        user_details: Optional[Dict[str, Any]] = None,
        ttl_seconds: int = CacheTTL.TOKEN_EXPIRY,
    ) -> str:
        """Issues a JWT for the specified user from FusionAuth using the Vend API."""
        client = cls.get_client()

        claims = {
            "sub": fusion_user_id,
            "aud": settings.fusionauth_client_id,
            "iss": settings.fusionauth_url,
            "roles": roles or [],
        }

        if user_details:
            claims.update(user_details)

        jwt_request = {"claims": claims, "timeToLiveInSeconds": ttl_seconds}

        response = client.vend_jwt(jwt_request)

        if response.was_successful():
            return response.success_response["token"]

        raise FusionAuthError(
            http_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.FUSION_AUTH_TOKEN_ERROR,
        )

    @classmethod
    def get_key(cls, key_id: str) -> Dict[str, Any]:
        """Retrieve a key from FusionAuth by ID."""
        client = cls.get_client()
        response = client.retrieve_key(key_id)

        if response.was_successful():
            return response.success_response["key"]

        raise FusionAuthError(
            http_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.KEY_RETRIEVAL_FAILED,
        )

    @classmethod
    def get_keys(cls) -> List[Dict[str, Any]]:
        """Retrieve all keys from FusionAuth."""
        client = cls.get_client()
        response = client.retrieve_keys()

        if response.was_successful():
            return response.success_response.get("keys", [])

        raise FusionAuthError(
            http_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve keys from FusionAuth",
        )
