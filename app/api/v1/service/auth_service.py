import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
import jwt
import pytz  # type: ignore
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service.fusionauth_service import FusionAuthService
from app.core.constants import (
    AuthConfig,
    CacheKeyTemplates,
    CacheValues,
    ErrorMessages,
    HeaderKeys,
    LoginParams,
    RequestParams,
)
from app.core.exceptions.exceptions import (
    DeviceNotRegisteredError,
    FailedToGenerateRefreshTokenError,
    InvalidServiceTokenError,
    UnauthorizedError,
)
from app.db.models.user_app import AppConsumer, User, UserAuthToken
from app.db.utils import execute_query
from app.settings import settings


class AuthService:
    """Service to handle user authentication, token generation, and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(
            password.encode(LoginParams.UTF8),
            bcrypt.gensalt(),
        ).decode(LoginParams.UTF8)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plain password against a bcrypt hash."""
        try:
            return bcrypt.checkpw(
                plain.encode(LoginParams.UTF8),
                hashed.encode(LoginParams.UTF8),
            )
        except Exception:
            return False

    @staticmethod
    async def generate_token(
        db_session: AsyncSession,
        user: User,
        client_id: str,
        cache: Redis,
        device_id: str | None = None,
        days_to_expire: int = settings.user_token_days_to_expire,
        partner_attrs: Dict[str, Any] | None = None,
    ) -> tuple[str, int]:
        """Generate a new JWT auth token for a user."""
        if partner_attrs is None:
            partner_attrs = {}
        # Fetch AppConsumer using SQLAlchemy
        result = await db_session.execute(
            select(AppConsumer).where(AppConsumer.client_id == client_id),
        )
        application = result.scalars().first()
        if not application:
            raise Exception(f"AppConsumer not found for client_id={client_id}")

        expiry = datetime.now(pytz.utc) + timedelta(days=int(days_to_expire))

        token_payload = {RequestParams.UUID: str(user.id), RequestParams.EXP: expiry}

        encoded_jwt = jwt.encode(
            token_payload,
            str(application.client_secret),
            algorithm=AuthConfig.ALGORITHM,
        )

        # Save token in table (SQLAlchemy style)
        user_token = UserAuthToken(
            device_id=device_id,
            token=encoded_jwt,
            uuid=user.id,
            app_consumer_id=application.id,  # assuming FK field
            expires_at=expiry,
            partner_id=partner_attrs.get(RequestParams.PARTNER_ID, CacheValues.EROS),
        )
        await db_session.merge(user_token)
        await db_session.commit()

        return encoded_jwt, int(expiry.timestamp())

    @staticmethod
    def decode_token(token: str, client_secret: str) -> Optional[Dict[str, Any]]:
        """Decode a JWT token."""
        try:
            # Try decoding with client secret (HS256) (legacy/local)
            return jwt.decode(token, client_secret, algorithms=[AuthConfig.ALGORITHM])
        except Exception:
            try:
                return FusionAuthService.verify_token(token)
            except Exception:
                return None

    @staticmethod
    async def verify_user_token(
        headers: Dict[str, Any],
        db_session: AsyncSession,
        device_id_arg: Optional[str] = None,
    ) -> str:
        """Verify user token from headers and return user_id."""
        api_client = headers.get(HeaderKeys.X_API_CLIENT) or headers.get(
            HeaderKeys.API_CLIENT,
        )
        api_token = headers.get(HeaderKeys.X_API_TOKEN) or headers.get(
            HeaderKeys.API_TOKEN,
        )
        device_id = (
            device_id_arg
            or headers.get(HeaderKeys.X_DEVICE_ID)
            or headers.get(
                HeaderKeys.DEVICE_ID,
            )
        )

        if not api_client or not api_token:
            raise UnauthorizedError

        # Check if device is registered
        from app.api.v1.service.device_service import DeviceService

        if not device_id:
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)
        # Validate device (resolving UUID if needed)
        await DeviceService.resolve_device_id(device_id, db_session)

        # Get client secret (HS256 fallback)
        result = await execute_query(
            UserQueries.GET_CLIENT_SECRET,
            {RequestParams.CLIENT_ID: api_client},
            db_session,
        )
        if not result:
            raise UnauthorizedError

        client_secret = result[0][RequestParams.CLIENT_SECRET]

        # Use updated decode_token which handles both
        # Run in thread if it does blocking I/O

        payload = await asyncio.to_thread(
            AuthService.decode_token,
            api_token,
            client_secret,
        )

        if not payload:
            raise UnauthorizedError

        uuid = payload.get(RequestParams.UUID)
        if not uuid and "sub" in payload:
            uuid = payload["sub"]

        if not isinstance(uuid, str):
            raise InvalidServiceTokenError
        return uuid

    @staticmethod
    async def free_token(
        user_uuid: str,
        token: str,
        db_session: AsyncSession,
        cache: Redis,
        device_id: Optional[str] = None,
    ) -> None:
        """Deactivate token in DB and remove from Redis."""
        # 1. Update DB (Deactivate specific token)
        # Note: We need a query that matches uuid + token.
        # UserQueries.DEACTIVATE_USER_AUTH_TOKEN covers this.
        await execute_query(
            UserQueries.DEACTIVATE_USER_AUTH_TOKEN,
            {RequestParams.USER_ID: user_uuid, RequestParams.TOKEN: token},
            db_session,
        )

        # 2. Remove from Redis
        # If device_id is known, we can remove the specific key.
        # If not, we might need to rely on the token structure or loop?
        # The Django code does: redis.lrem(token_obj.uuid, 1, auth_token)
        # and redis.remove_key(auth_token)
        # Our redis pattern is `auth:{user_uuid}:{device_id}` -> token
        # If we only have token, we can't easily find the key without
        # scanning or storing reverse mapping.
        # However, `logout` usually provides device_id.
        if device_id:
            await cache.delete(
                CacheKeyTemplates.USER_AUTH_TOKEN.format(
                    user_uuid=user_uuid,
                    device_id=device_id,
                ),
            )
        else:
            # Fallback: Scan or ignore?
            # For now, we assume device_id is provided or we accept
            # that redis key expires naturally.
            pass

    @staticmethod
    async def create_refresh_session(
        db_session: AsyncSession,
        user_id: str,
        device_id: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_claim_id: str | None = None,
    ) -> str:
        """
        Create a new refresh token/session.

        Invalidates old ones for this device.
        """

        # 1. Generate new Refresh Token (JWT via FusionAuth RS256)
        # Old sessions will be updated or deactivated implicitly if we reuse the row.

        # 2. Generate new Refresh Token (JWT via FusionAuth RS256)
        expiry_seconds = settings.user_token_days_to_expire * 24 * 60 * 60
        expiry = datetime.utcnow() + timedelta(seconds=expiry_seconds)

        # Unique identifier
        jti = str(uuid.uuid4())

        # Use device_claim_id if provided, else device_id for the token claim
        claims = {
            "device_id": device_claim_id or device_id,
            "type": "refresh",
            "jti": jti,
        }

        # Issue token using FusionAuth
        refresh_token = await asyncio.to_thread(
            FusionAuthService.issue_token,
            fusion_user_id=user_id,
            user_details=claims,
            ttl_seconds=expiry_seconds,
        )

        if not refresh_token:
            raise FailedToGenerateRefreshTokenError

        # 3. Store in DB (Delete existing then Insert)
        # Delete old/duplicate sessions first to prevent unique constraint violations
        await execute_query(
            UserQueries.DEACTIVATE_OLD_SESSIONS,
            {"user_id": user_id, "device_id": device_id},
            db_session,
        )

        # Insert new session
        await execute_query(
            UserQueries.INSERT_AUTH_SESSION,
            {
                "user_id": user_id,
                "device_id": device_id,
                "auth_token": refresh_token,
                "auth_token_expiry": expiry,
                "user_agent": user_agent,
                "ip_address": ip_address,
            },
            db_session,
        )

        return refresh_token

    @staticmethod
    async def refresh_access_token(
        db_session: AsyncSession,
        refresh_token: str,
        device_id: str,
    ) -> tuple[str, str, int]:
        """Validates refresh token and issues new access token."""
        # 0. Decode and Verify Signature (RS256 via FusionAuth Public Key)

        try:
            # Verify signature using FusionAuth Public Keys (cached)
            payload = await asyncio.to_thread(
                FusionAuthService.verify_token,
                refresh_token,
            )

            # Basic validation
            if payload.get("type") != "refresh":
                raise InvalidServiceTokenError(message=ErrorMessages.INVALID_TOKEN_TYPE)
            if str(payload.get("device_id")) != str(device_id):
                # Device mismatch
                pass

        except Exception as e:
            raise UnauthorizedError("Invalid or expired refresh token") from e

        # 1. Validate DB (ensure not revoked/rotated)
        rows = await execute_query(
            UserQueries.GET_AUTH_SESSION_BY_TOKEN,
            {"refresh_token": refresh_token, "device_id": device_id},
            db_session,
        )
        if not rows:
            raise UnauthorizedError(message=ErrorMessages.REFRESH_TOKEN_INVALID)

        session = rows[0]
        user_id = str(session["user_id"])

        # 2. Call FusionAuth (for new Access Token)

        fa_token = await asyncio.to_thread(
            FusionAuthService.issue_token,
            user_id,
            user_details={"device_id": device_id},
        )
        if not fa_token:
            raise UnauthorizedError(message=ErrorMessages.ACCESS_TOKEN_ISSUE_FAILED)

        expires_at = int(time.time()) + 600

        # 3. Rotate Refresh Token
        new_refresh_token = await AuthService.create_refresh_session(
            db_session=db_session,
            user_id=user_id,
            device_id=device_id,
            user_agent=session.get("user_agent"),  # get from DictRow
            ip_address=session.get("ip_address"),
        )

        return fa_token, new_refresh_token, expires_at
