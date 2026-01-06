from typing import Any, Dict

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions.exceptions import UnauthorizedError
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
