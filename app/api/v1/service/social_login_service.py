from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from loguru import logger

from app.api.queries import UserQueries
from app.db.utils import execute_query
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.google_oauth_service import GoogleOAuthService
from app.api.v1.service.apple_oauth_service import AppleOAuthService


class SocialLoginService:
    @staticmethod
    async def google_login(
        google_service: GoogleOAuthService,
        request_data: dict,
        db_session: AsyncSession,
        cache: Redis,
    ):
        """
        Handle Google Social Login business logic.
        """
        # 1. Verify Google ID Token
        await google_service.verify_id_token(request_data["uid"])

        # 2. Get user by social login
        social_id = google_service.get_uid()
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
            # We check if user exists with the same email first (optional based on requirements, 
            # but usually social login should link to existing account if email matches)
            email = google_service.get_email()
            if email:
                email_rows = await execute_query(
                    UserQueries.GET_USER_BY_EMAIL, {"email": email}, db_session
                )
                if email_rows:
                    user = dict(email_rows[0])
                    # If user exists by email, we should still update/create identity provider later

            if not user:
                # Actually signup
                signup_rows = await execute_query(
                    UserQueries.SIGNUP_WITH_SOCIAL_DATA,
                    {
                        "provider": provider,
                        "social_id": social_id,
                        "email": email,
                        "name": google_service.get_name(),
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
            raise Exception("Failed to find or create user via social login")

        user_id = user["id"]

        # 4. Create or update identity provider
        await execute_query(
            UserQueries.UPSERT_SOCIAL_IDENTITY_PROVIDER,
            {
                "user_id": user_id,
                "provider": provider,
                "social_id": social_id,
                "token": google_service.get_token(),
            },
            db_session,
        )

        # 5. Generate Auth Token
        token, expires_at = await AuthService.generate_token(
            user_uuid=user_id,
            client_id=request_data["client_id"],
            db_session=db_session,
            cache=cache,
            device_id=request_data["device_id"],
        )

        # Get user details for response
        profile_rows = await execute_query(
            UserQueries.GET_USER_PROFILE, {"user_id": user_id}, db_session
        )
        user_profile = dict(profile_rows[0]) if profile_rows else {}

        return {
            "auth_token": token,
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
        request_data: dict,
        db_session: AsyncSession,
        cache: Redis,
    ):
        """
        Handle Apple Social Login business logic.
        """
        # 1. Verify Apple ID Token
        await apple_service.verify_id_token(request_data["uid"])

        # 2. Get user by social login
        social_id = apple_service.get_uid()
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
            email = apple_service.get_email()
            
            # Note: Apple sometimes hides email (private relay), so email could be None or a privaterelay email.
            if email:
                email_rows = await execute_query(
                    UserQueries.GET_USER_BY_EMAIL, {"email": email}, db_session
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
                        "name": apple_service.get_name(), # Likely None for existing Apple logic unless we extend
                        "country": request_data.get("country"),
                        "platform": request_data.get("platform"),
                        "user_agent": request_data.get("user_agent"),
                    },
                    db_session,
                )
                if signup_rows:
                    user = dict(signup_rows[0])

        if not user:
             raise Exception("Failed to find or create user via social login")

        user_id = user["id"]

        # 4. Create or update identity provider
        await execute_query(
            UserQueries.UPSERT_SOCIAL_IDENTITY_PROVIDER,
            {
                "user_id": user_id,
                "provider": provider,
                "social_id": social_id,
                "token": apple_service.get_token(),
            },
            db_session,
        )

        # 5. Generate Auth Token
        token, expires_at = await AuthService.generate_token(
            user_uuid=user_id,
            client_id=request_data["client_id"],
            db_session=db_session,
            cache=cache,
            device_id=request_data["device_id"],
        )

        # Get user details for response
        profile_rows = await execute_query(
            UserQueries.GET_USER_PROFILE, {"user_id": user_id}, db_session
        )
        user_profile = dict(profile_rows[0]) if profile_rows else {}

        return {
            "auth_token": token,
            "user": {
                "user_id": str(user_id),
                "email": user_profile.get("email"),
                "name": user_profile.get("name"),
                "image": user_profile.get("image"),
            },
        }
