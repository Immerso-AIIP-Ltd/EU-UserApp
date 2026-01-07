from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service.auth_service import AuthService
from app.core.constants import LoginParams, RequestParams
from app.core.exceptions import (
    PasswordsDoNotMatchError,
)
from app.db.utils import execute_query


class ChangePasswordService:
    """Service to handle user password changes."""

    @staticmethod
    async def change_password(
        user_uuid: str,
        new_password: str,
        new_password_confirm: str,
        db_session: AsyncSession,
    ) -> None:
        """Update a user's password after verifying both new passwords match."""
        # 1. Verify new passwords match
        if new_password != new_password_confirm:
            raise PasswordsDoNotMatchError

        # 2. Hash new password
        new_hash = AuthService.hash_password(new_password)

        # 3. Update database
        await execute_query(
            UserQueries.UPDATE_USER_PASSWORD,
            {RequestParams.USER_ID: user_uuid, LoginParams.PASSWORD: new_hash},
            db_session,
        )
