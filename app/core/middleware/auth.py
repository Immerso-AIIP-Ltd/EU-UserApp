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
    token_str = None
    if token:
        token_str = token.credentials
    elif request.headers.get("x-api-token"):
        # Fallback to x-api-token
        token_str = request.headers.get("x-api-token")
    
    if not token_str:
        # raise UnauthorizedError(detail="Missing authentication token")
        return {}

    try:
        # Try verifying with FusionAuth first
        try:
            from app.api.v1.service.fusionauth_service import FusionAuthService
            import asyncio
            # Run sync verification in thread
            payload = await asyncio.to_thread(FusionAuthService.verify_token, token_str)
            if "sub" in payload and "user_id" not in payload:
                payload["user_id"] = payload["sub"]
            return payload
        except Exception:
            # If FusionAuth fails or isn't configured, fall back to local validation
            pass

        payload = jwt.decode(
            token_str,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if "sub" in payload and "user_id" not in payload:
            payload["user_id"] = payload["sub"]
        return payload
    except jwt.ExpiredSignatureError as e:
        raise UnauthorizedError(detail="Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(detail="Invalid token") from e
    except Exception as e:
        raise UnauthorizedError(detail=f"Could not validate credentials: {e!s}") from e
