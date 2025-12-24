import hashlib
from datetime import datetime

from app.api.v1.register import links
import logging

logger = logging.getLogger(__name__)


class UserAuthService:

    @staticmethod
    async def login(
        session: AsyncSession,
        user,
        payload: dict,
        client,
        device_id: str | None,
        request,
        password: str | None = None,
    ):

        # Password validation (skip for social login)
        if password:
            sha1_password = hashlib.sha1(password.encode("utf-8")).hexdigest()

            # Legacy SHA1 check
            if user.password != sha1_password:
                raise InvalidCredentials()

            # bcrypt upgrade (safe)
            try:
                if not AuthService.check_password(password, user.encrypted_password):
                    user.encrypted_password = AuthService.get_hashed_password(password)
            except Exception:
                user.encrypted_password = AuthService.get_hashed_password(password)

            payload["password"] = sha1_password

        # Ensure device exists (FK SAFE)
        if device_id:
            await DeviceService.ensure_device(
                session=session,
                device_id=device_id,
                user_id=user.uuid,
                payload=payload,
                client_ip=request.client.host,
            )

            payload.update(
                await DeviceService.get_device_attrs(session, device_id)
            )

        # Call legacy login API (optional)
        legacy_token = legacy_secret = ""
        skipped_legacy_login = True

        if payload.get("provider") != "apple":
            try:
                logger.info("Calling legacy login API")
                response = call_legacy_api(
                    links.LEGACY_LOGIN,
                    payload,
                    consumer_key=client.legacy_key,
                    consumer_secret=client.legacy_secret,
                )
                legacy_token = response["token"]
                legacy_secret = response["token_secret"]
                skipped_legacy_login = False
            except Exception as e:
                logger.warning(f"Legacy login skipped: {e}")

        # Generate JWT + save auth token
        encoded_jwt, expiry = await AuthService.generate_token(
            session=session,
            user=user,
            client=client,
            device_id=device_id,
        )

        # Link device + legacy tokens
        if device_id:
            await DeviceService.link_device_to_user(
                session=session,
                device_id=device_id,
                user_id=user.uuid,
                auth_token=encoded_jwt,
                skipped_legacy_login=skipped_legacy_login,
            )

        await AuthService.map_legacy_tokens(
            session=session,
            user_id=user.uuid,
            auth_token=encoded_jwt,
            legacy_token=legacy_token,
            legacy_secret=legacy_secret,
        )

        # Create PG user if missing
        await UserRegisterService.create_pg_user(session, user)

        # Commit transaction
        await session.commit()

        return {
            "auth_token": encoded_jwt,
            "token": legacy_token,
            "token_secret": legacy_secret,
            "auth_token_expiry": expiry,
        }
