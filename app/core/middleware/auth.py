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
        payload = jwt.decode(
            token.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(detail="Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedError(detail="Invalid token")
    except Exception as e:
        raise UnauthorizedError(detail=f"Could not validate credentials: {e!s}")
