from typing import Any, Dict

import jwt
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions.exceptions import (
    InvalidServiceTokenError,
    UnauthorizedError,
    UserTokenNotFoundError,
)
from app.settings import settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    token: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency to get the currently authenticated user.

    Decodes and verifies the JWT token from the Authorization header.
    """
    if not token:
        raise UnauthorizedError(detail="Missing authentication token")

    try:
        return jwt.decode(
            token.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as e:
        raise UnauthorizedError(detail="Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(detail="Invalid token") from e
    except Exception as e:
        raise UnauthorizedError(detail=f"Could not validate credentials: {e!s}") from e


async def get_user_from_x_token(
    request: Request,
    x_api_token: str = Header(..., alias="x-api-token"),
) -> Dict[str, Any]:
    """
    Dependency to get the currently authenticated user from x-api-token.

    Decodes the JWT token from the x-api-token header WITHOUT signature verification.
    This relies on the gateway having already validated the token.
    """
    if not x_api_token:
        # This case is largely handled by validate_common_headers or the
        # Header(...) required field
        raise UserTokenNotFoundError

    try:
        # Decode without verification
        return jwt.decode(
            x_api_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": False},
        )
    except jwt.DecodeError as e:
        raise InvalidServiceTokenError from e
    except Exception as e:
        # Fallback to unauthorized for unknown decoding errors
        raise UnauthorizedError(detail=f"Could not decode token: {e!s}") from e
