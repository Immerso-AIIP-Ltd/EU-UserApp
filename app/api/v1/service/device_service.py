import contextlib
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service.device_redis_service import DeviceTokenRedisService
from app.core.constants import ErrorMessages
from app.core.exceptions.exceptions import (
    DeviceAlreadyRegisteredError,
    DeviceNotRegisteredError,
)
from app.db.utils import execute_query


class DeviceService:
    """Service to handle device registration, updates, and user linking."""

    @staticmethod
    async def is_device_registered(device_id: str, db_session: AsyncSession) -> bool:
        """Check if a device is already registered in the database."""
        rows = await execute_query(
            UserQueries.CHECK_DEVICE_EXISTS,
            {"id": device_id},
            db_session,
        )
        return bool(rows)

    @staticmethod
    async def create_device(
        device_id: str,
        db_session: AsyncSession,
        cache: Redis | None,
        **attrs: Any,
    ) -> dict[str, Any]:
        """Creates a new device."""
        if await DeviceService.is_device_registered(device_id, db_session):
            raise DeviceAlreadyRegisteredError("Device already registered")

        # Prepare default values matching the query params
        params = {
            "device_id": device_id,
            "device_type": attrs.get("device_type", "android"),
            "device_name": attrs.get("device_name", ""),
            "platform": attrs.get("platform", "android"),
            "device_ip": attrs.get("device_ip", None),
            "is_rooted": attrs.get("is_rooted", False),
            "is_jailbroken": attrs.get("is_jailbroken", False),
            "push_token": attrs.get("push_token", None),
            "user_id": attrs.get("user_id", None),
            "user_token": attrs.get("user_token", None),
        }

        await execute_query(UserQueries.INSERT_DEVICE, params, db_session)
        return params

    @staticmethod
    async def update_device(
        device_id: str,
        db_session: AsyncSession,
        cache: Redis,
        **kwargs: Any,
    ) -> None:
        """Updates device details."""
        params = {
            "device_id": device_id,
            "device_type": kwargs.get("device_type"),
            "device_name": kwargs.get("device_name"),
            "push_token": kwargs.get("push_token"),
        }
        await execute_query(UserQueries.UPDATE_DEVICE, params, db_session)

    @staticmethod
    async def get_device(device_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """Gets device by ID."""
        rows = await execute_query(
            UserQueries.GET_DEVICE_BY_ID,
            {"id": device_id},
            db_session,
        )
        if not rows:
            raise DeviceNotRegisteredError("Device not registered")
        return dict(rows[0])

    @staticmethod
    async def get_device_by_uuid(
        device_uuid: str,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """Gets device by UUID (PK)."""
        if not device_uuid:
            raise DeviceNotRegisteredError("Device UUID missing")
        rows = await execute_query(
            UserQueries.GET_DEVICE_BY_UUID,
            {"id": device_uuid},
            db_session,
        )
        if not rows:
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)
        return dict(rows[0])

    @staticmethod
    async def resolve_device_id(
        device_identifier: str,
        db_session: AsyncSession,
    ) -> str:
        """
        Resolves device identifier to the Serial Number (device_id string).

        Refactored to assume input is likely the Serial Number,
        which identifies the device in DB.
        """
        if not device_identifier:
            raise DeviceNotRegisteredError("Device Identifier missing")

        # Just verify it exists using the Serial Number lookup
        try:
            # get_device uses serial_number lookup now (Step 1033)
            await DeviceService.get_device(device_identifier, db_session)
            return device_identifier
        except Exception:
            raise DeviceNotRegisteredError(
                ErrorMessages.DEVICE_NOT_REGISTERED,
            ) from None

    @staticmethod
    async def link_device_to_user(
        db_session: AsyncSession,
        device_id: str,
        user_uuid: str,
        cache: Redis | None = None,
        auth_token: str | None = None,
        skipped_legacy_login: bool = False,
        uuid: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Links a device to a user and syncs token to Redis."""
        # Handle aliases
        final_user_uuid = user_uuid or uuid
        final_session = db_session or session

        if not final_user_uuid or not final_session:
            raise ValueError("User UUID and Session required")

        exists = await DeviceService.is_device_registered(device_id, final_session)
        if not exists:
            # logic to handle non-existent device if needed, or pass
            pass

        # Update DB
        await execute_query(
            UserQueries.LINK_DEVICE_TO_USER,
            {
                "device_id": device_id,
                "user_id": final_user_uuid,
                "user_token": auth_token,
            },
            final_session,
        )

        # Get updated device to sync
        with contextlib.suppress(Exception):
            device = await DeviceService.get_device(device_id, final_session)
            # Auto-sync to Redis
            if device.get("push_token") and cache:
                redis_service = DeviceTokenRedisService(cache)
                await redis_service.store_device_token_in_redis(device, final_user_uuid)

    @staticmethod
    async def deactivate_device(
        device_id: str,
        user_uuid: str,
        db_session: AsyncSession,
        cache: Redis,
    ) -> None:
        """Deactivates a device for a user."""
        try:
            device = await DeviceService.get_device(device_id, db_session)
        except DeviceNotRegisteredError:
            return

        await execute_query(
            UserQueries.DEACTIVATE_DEVICE,
            {"device_id": device_id, "user_id": user_uuid},
            db_session,
        )

        if device.get("push_token"):
            with contextlib.suppress(Exception):
                redis_service = DeviceTokenRedisService(cache)
                await redis_service.remove_device_token_from_redis(device, user_uuid)

    @staticmethod
    async def ensure_device(
        session: AsyncSession,
        device_id: str,
        user_id: str,
        payload: dict[str, Any],
        client_ip: str | None,
    ) -> None:
        """Ensures device exists, creating it if necessary."""
        if not await DeviceService.is_device_registered(device_id, session):
            await DeviceService.create_device(
                device_id,
                session,
                None,  # cache placeholder
                device_type=payload.get("device_type", "android"),
                device_name=payload.get("device_name", ""),
                platform=payload.get("platform", "android"),
                device_ip=client_ip,
                push_token=payload.get("push_token"),
            )

    @staticmethod
    async def get_device_attrs(session: AsyncSession, device_id: str) -> dict[str, Any]:
        """Get device attributes for payload update."""
        try:
            device = await DeviceService.get_device(device_id, session)
            return {
                "device_type": device.get("device_type"),
                "device_name": device.get("device_name"),
                "push_token": device.get("push_token"),
            }
        except DeviceNotRegisteredError:
            return {}
