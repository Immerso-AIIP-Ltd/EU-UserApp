from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service.auth_service import AuthService
from app.core.exceptions.exceptions import PasswordsDoNotMatchError
from app.db.utils import execute_query


class ChangePasswordService:

    @staticmethod
    async def change_password(
        user_uuid: str,
        new_password: str,
        new_password_confirm: str,
        db_session: AsyncSession,
    ) -> None:
        # 1. Verify new passwords match
        if new_password != new_password_confirm:
            raise PasswordsDoNotMatchError()

        # 2. Hash new password
        new_hash = AuthService.hash_password(new_password)

        # 3. Update database
        await execute_query(
            UserQueries.UPDATE_USER_PASSWORD,
            {"user_id": user_uuid, "password": new_hash},
            db_session,
        )
