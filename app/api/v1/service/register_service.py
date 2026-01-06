import uuid
from datetime import datetime

import pytz  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.register.task import (
    get_hashed_password,
    get_sha1_hash,
)
from app.db.models.user_app import User


class UserProfileService:
    @staticmethod
    def set_first_name_and_last_name(name: str | None) -> tuple[str | None, str | None]:
        if name:
            name_array = name.rsplit(" ", 1)
            if len(name_array) > 1:
                return name_array[0], name_array[1]
            else:
                return name_array[0] if name_array[0] else None, None
        else:
            return None, None


class UserRegisterService:

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str | None = None,
        mobile: str | None = None,
        password: str = "",
        name: str = "",
        calling_code: str | None = None,
        country: str | None = None,
        platform: str | None = None,
        activated: str = "YES",
        user_agent: str | None = None,
    ) -> User:

        firstname, lastname = UserProfileService.set_first_name_and_last_name(name)
        user_uuid = uuid.uuid4()
        now = datetime.now(pytz.utc)

        # Note: 'get_random_bigint' was in service.py. implementing locally or importing if needed.
        # Simple random implementation
        import random

        BIGINT_LIMIT = 2**63
        activation_code = random.randint(0, BIGINT_LIMIT)

        legacy_user = User(
            uuid=user_uuid,
            email=email,
            mobile=mobile,
            calling_code=calling_code,
            activation_code=activation_code,
            country=country,
            registration_datetime=now,
            updated_datetime=now,
            password=await get_sha1_hash(password),
            encrypted_password=await get_hashed_password(password),
            reg_user_agent=user_agent,
            activated=activated,
            name=name,
            firstname=firstname,
            lastname=lastname,
        )

        db.add(legacy_user)
        await db.flush()

        await UserRegisterService.create_pg_user(
            db=db,
            legacy_user=legacy_user,
            platform=platform,
        )

        await db.commit()
        return legacy_user

    @staticmethod
    async def create_pg_user(
        db: AsyncSession,
        legacy_user: User,
        platform: str | None = None,
    ) -> None:
        """
        Creates/Syncs Postgres user if needed.
        Currently a placeholder as implementation was missing.
        """
        # Logic to create additional postgres user records if separated from 'User' model
        # For now, we assume 'User' model IS the PG user.
