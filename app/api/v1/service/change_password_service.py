from app.api.queries import UserQueries
from app.api.v1.service.auth_service import AuthService
from app.core.exceptions import (
    PasswordsDoNotMatch,
    InvalidOldPassword,
)
from app.db.utils import execute_query
from sqlalchemy.ext.asyncio import AsyncSession


class ChangePasswordService:

    @staticmethod
    async def change_password(
        user_uuid: str,
        old_password: str | None,
        new_password: str,
        new_password_confirm: str,
        db_session: AsyncSession,
    ):
        # 1. Verify new passwords match
        if new_password != new_password_confirm:
            raise PasswordsDoNotMatch()

        # 2. Verify old password if provided
        if old_password:
            rows = await execute_query(
                UserQueries.GET_USER_PASSWORD_HASH,
                {"user_id": user_uuid},
                db_session
            )
            if not rows:
                raise InvalidOldPassword()
            
            stored_hash = rows[0]["password"]
            if not AuthService.verify_password(old_password, stored_hash):
                raise InvalidOldPassword()

        # 3. Hash new password
        new_hash = AuthService.hash_password(new_password)

        # 4. Update database
        await execute_query(
            UserQueries.UPDATE_USER_PASSWORD,
            {"user_id": user_uuid, "password": new_hash},
            db_session
        )
