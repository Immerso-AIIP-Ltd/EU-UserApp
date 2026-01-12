import asyncio
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service.apple_oauth_service import AppleOAuthService
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.facebook_oauth_service import FacebookOAuthService
from app.api.v1.service.fusionauth_service import FusionAuthService
from app.api.v1.service.google_oauth_service import GoogleOAuthService
from app.core.constants import DeviceNames, ErrorMessages
from app.db.models.user_app import User
from app.db.utils import execute_query


class SocialLoginService:
    """Service to handle social login business logic."""

    @staticmethod
    async def google_login(
        google_service: GoogleOAuthService,
        request_data: dict[str, Any],
        db_session: AsyncSession,
        cache: Redis,
    ) -> dict[str, Any]:
        """Handle Google Social Login business logic."""
        # 1. Verify Google ID Token
        await google_service.verify_id_token()

        # 2. Get user by social login
        social_id = await google_service.get_uid()
        provider = google_service.NAME

        rows = await execute_query(
            UserQueries.GET_USER_BY_SOCIAL_IDENTITY,
            {"provider": provider, "social_id": social_id},
            db_session,
        )

        user = None
        if rows:
            user = dict(rows[0])
        else:
            # 3. New user, signup with social
            # We check if user exists with the same email first (optional based on
            # requirements, but usually social login should link to existing
            # account if email matches)
            email = await google_service.get_email()
            if email:
                email_rows = await execute_query(
                    UserQueries.GET_USER_BY_EMAIL,
                    {"email": email},
                    db_session,
                )
                if email_rows:
                    user = dict(email_rows[0])
                    # If user exists by email, we should still update/create identity
                    # provider later

            if not user:
                # Actually signup
                signup_rows = await execute_query(
                    UserQueries.SIGNUP_WITH_SOCIAL_DATA,
                    {
                        "provider": provider,
                        "social_id": social_id,
                        "email": email,
                        "name": await google_service.get_name(),
                        "country": request_data.get("country"),
                        "platform": request_data.get("platform"),
                        "user_agent": request_data.get("user_agent"),
                    },
                    db_session,
                )
                if signup_rows:
                    user = dict(signup_rows[0])

        if not user:
            # This shouldn't happen if signup_with_social works
            raise Exception(ErrorMessages.FUSION_AUTH_REGISTRATION_ERROR)

        user_id = user["id"]

        # 4. Create or update identity provider
        await execute_query(
            UserQueries.UPSERT_SOCIAL_IDENTITY_PROVIDER,
            {
                "user_id": user_id,
                "provider": provider,
                "social_id": social_id,
                "token": await google_service.get_token(),
            },
            db_session,
        )

        # 5. Generate Auth Token
        # 5. Generate Auth Token
        from app.db.models.user_app import User

        token, expires_at = await AuthService.generate_token(
            user=User(id=user_id),
            client_id=request_data["client_id"],
            db_session=db_session,
            cache=cache,
            device_id=request_data["device_id"],
        )

        # FusionAuth Integration
        try:
            user_uuid_str = str(user_id)
            user_email = user.get("email")

            # 1. Sync User (Ensure exists)
            await asyncio.to_thread(
                FusionAuthService.create_fusion_user,
                user_uuid_str,
                user_email,
            )

            # 2. Issue Token
            fa_token = await asyncio.to_thread(
                FusionAuthService.issue_token,
                user_uuid_str,
            )

            if fa_token:
                token = fa_token
        except Exception as e:
            raise Exception(ErrorMessages.FUSION_AUTH_TOKEN_ERROR) from e

        # Get user details for response
        profile_rows = await execute_query(
            UserQueries.GET_USER_PROFILE,
            {"user_id": user_id},
            db_session,
        )
        user_profile = dict(profile_rows[0]) if profile_rows else {}

        # Generate Refresh Token
        refresh_token = await AuthService.create_refresh_session(
            db_session=db_session,
            user_id=str(user_id),
            device_id=request_data.get("device_id") or DeviceNames.UNKNOWN_DEVICE,
            user_agent=request_data.get("user_agent"),
        )

        return {
            "auth_token": token,
            "refresh_token": refresh_token,
            "user": {
                "user_id": str(user_id),
                "email": user_profile.get("email"),
                "name": user_profile.get("name"),
                "image": user_profile.get("image"),
            },
        }

    @staticmethod
    async def apple_login(
        apple_service: AppleOAuthService,
        request_data: dict[str, Any],
        db_session: AsyncSession,
        cache: Redis,
    ) -> dict[str, Any]:
        """Handle Apple Social Login business logic."""
        # 1. Verify Apple ID Token
        await apple_service.verify_id_token(request_data["uid"])

        # 2. Get user by social login
        social_id = await apple_service.get_uid()
        provider = apple_service.NAME

        rows = await execute_query(
            UserQueries.GET_USER_BY_SOCIAL_IDENTITY,
            {"provider": provider, "social_id": social_id},
            db_session,
        )

        user = None
        if rows:
            user = dict(rows[0])
        else:
            # 3. New user, signup with social
            email = await apple_service.get_email()

            # Note: Apple sometimes hides email (private relay), so email could
            # be None or a privaterelay email.
            if email:
                email_rows = await execute_query(
                    UserQueries.GET_USER_BY_EMAIL,
                    {"email": email},
                    db_session,
                )
                if email_rows:
                    user = dict(email_rows[0])

            if not user:
                signup_rows = await execute_query(
                    UserQueries.SIGNUP_WITH_SOCIAL_DATA,
                    {
                        "provider": provider,
                        "social_id": social_id,
                        "email": email,
                        "name": await apple_service.get_name(),
                        "country": request_data.get("country"),
                        "platform": request_data.get("platform"),
                        "user_agent": request_data.get("user_agent"),
                    },
                    db_session,
                )
                if signup_rows:
                    user = dict(signup_rows[0])

        if not user:
            raise Exception(ErrorMessages.FUSION_AUTH_REGISTRATION_ERROR)

        user_id = user["id"]

        # 4. Create or update identity provider
        await execute_query(
            UserQueries.UPSERT_SOCIAL_IDENTITY_PROVIDER,
            {
                "user_id": user_id,
                "provider": provider,
                "social_id": social_id,
                "token": await apple_service.get_token(),
            },
            db_session,
        )

        # 5. Generate Auth Token
        from app.db.models.user_app import User

        token, expires_at = await AuthService.generate_token(
            user=User(id=user_id),
            client_id=request_data["client_id"],
            db_session=db_session,
            cache=cache,
            device_id=request_data["device_id"],
        )

        # FusionAuth Integration
        try:
            user_uuid_str = str(user_id)
            user_email = user.get("email")

            # 1. Sync User (Ensure exists)
            await asyncio.to_thread(
                FusionAuthService.create_fusion_user,
                user_uuid_str,
                user_email,
            )

            # 2. Issue Token
            fa_token = await asyncio.to_thread(
                FusionAuthService.issue_token,
                user_uuid_str,
            )

            if fa_token:
                token = fa_token
        except Exception as e:
            raise Exception(ErrorMessages.FUSION_AUTH_TOKEN_ERROR) from e

        # Get user details for response
        profile_rows = await execute_query(
            UserQueries.GET_USER_PROFILE,
            {"user_id": user_id},
            db_session,
        )
        user_profile = dict(profile_rows[0]) if profile_rows else {}

        # Generate Refresh Token
        refresh_token = await AuthService.create_refresh_session(
            db_session=db_session,
            user_id=str(user_id),
            device_id=request_data.get("device_id") or DeviceNames.UNKNOWN_DEVICE,
            user_agent=request_data.get("user_agent"),
        )

        return {
            "auth_token": token,
            "refresh_token": refresh_token,
            "user": {
                "user_id": str(user_id),
                "email": user_profile.get("email"),
                "name": user_profile.get("name"),
                "image": user_profile.get("image"),
            },
        }

    @staticmethod
    async def facebook_login(
        facebook_service: FacebookOAuthService,
        request_data: dict[str, Any],
        db_session: AsyncSession,
        cache: Redis,
    ) -> dict[str, Any]:
        """Handle Facebook Social Login business logic."""
        # 1. Verify Facebook Access Token
        # Facebook verification matches ID against UID inside verify_access_token
        # so we pass uid
        await facebook_service.verify_access_token(request_data["uid"])

        # 2. Get user by social login
        social_id = await facebook_service.get_uid()
        provider = facebook_service.NAME

        rows = await execute_query(
            UserQueries.GET_USER_BY_SOCIAL_IDENTITY,
            {"provider": provider, "social_id": social_id},
            db_session,
        )

        user = None
        if rows:
            user = dict(rows[0])
        else:
            # 3. New user, signup with social
            email = await facebook_service.get_email()

            if email:
                email_rows = await execute_query(
                    UserQueries.GET_USER_BY_EMAIL,
                    {"email": email},
                    db_session,
                )
                if email_rows:
                    user = dict(email_rows[0])

            if not user:
                signup_rows = await execute_query(
                    UserQueries.SIGNUP_WITH_SOCIAL_DATA,
                    {
                        "provider": provider,
                        "social_id": social_id,
                        "email": email,
                        "name": await facebook_service.get_name(),
                        "country": request_data.get("country"),
                        "platform": request_data.get("platform"),
                        "user_agent": request_data.get("user_agent"),
                    },
                    db_session,
                )
                if signup_rows:
                    user = dict(signup_rows[0])

        if not user:
            raise Exception(ErrorMessages.FUSION_AUTH_REGISTRATION_ERROR)

        user_id = user["id"]

        # 5. Create or update identity provider
        await execute_query(
            UserQueries.UPSERT_SOCIAL_IDENTITY_PROVIDER,
            {
                "user_id": user_id,
                "provider": provider,
                "social_id": social_id,
                "token": await facebook_service.get_token(),
            },
            db_session,
        )

        # 5. Generate Auth Token
        token, expires_at = await AuthService.generate_token(
            user=User(id=user_id),
            client_id=request_data["client_id"],
            db_session=db_session,
            cache=cache,
            device_id=request_data["device_id"],
        )

        # FusionAuth Integration
        try:
            user_uuid_str = str(user_id)
            user_email = user.get("email")

            # 1. Sync User (Ensure exists)
            await asyncio.to_thread(
                FusionAuthService.create_fusion_user,
                user_uuid_str,
                user_email,
            )

            # 2. Issue Token
            fa_token = await asyncio.to_thread(
                FusionAuthService.issue_token,
                user_uuid_str,
            )

            if fa_token:
                token = fa_token
        except Exception as e:
            raise Exception(ErrorMessages.FUSION_AUTH_TOKEN_ERROR) from e

        # Get user details for response
        profile_rows = await execute_query(
            UserQueries.GET_USER_PROFILE,
            {"user_id": user_id},
            db_session,
        )
        user_profile = dict(profile_rows[0]) if profile_rows else {}

        # Generate Refresh Token
        refresh_token = await AuthService.create_refresh_session(
            db_session=db_session,
            user_id=str(user_id),
            device_id=request_data.get("device_id") or DeviceNames.UNKNOWN_DEVICE,
            user_agent=request_data.get("user_agent"),
        )

        return {
            "auth_token": token,
            "refresh_token": refresh_token,
            "user": {
                "user_id": str(user_id),
                "email": user_profile.get("email"),
                "name": user_profile.get("name"),
                "image": user_profile.get("image"),
            },
        }
