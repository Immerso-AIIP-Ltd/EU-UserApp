from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SuccessMessages
from tests.api.mock_data import MockModel
from tests.api.test_helper import assert_endpoint_success, get_auth_headers


@pytest.mark.anyio
async def test_join_waitlist_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "device_id": "test_device",
        "email_id": "waitlist@example.com",
        "name": "Waitlist User",
    }
    payload = {"key": "k", "data": "d"}

    headers = get_auth_headers(device_id="test_device")
    with patch(
        "app.api.v1.friend_invite_joinwaitlist.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views.execute_query",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "app.api.v1.friend_invite_joinwaitlist.views.GenerateOtpService.generate_otp",
        new_callable=AsyncMock,
    ):

        # Mock for 3 calls: check device, check email, insert
        mock_exec.side_effect = [
            [], # Call 1: check_device_and_email
            [], # Call 2: check_email
            [MockModel(queue_number=123, is_verified=False)], # Call 3: insert
        ]

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/auth/social/waitlist",
            SuccessMessages.WAITLIST_OTP_SENT.format("email"),
            payload=payload,
            headers=headers,
        )

@pytest.mark.anyio
async def test_friend_invite_success(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    payload = {
        "invited_list": [
            {"email": "friend@example.com"},
        ],
    }
    headers = get_auth_headers(device_id="test_device")

    mock_waitlist_entry = MockModel(
        email="inviter@example.com",
        queue_number=123,
    )

    with patch(
        "app.api.v1.friend_invite_joinwaitlist.views._resolve_inviter",
        new_callable=AsyncMock,
        return_value=(mock_waitlist_entry, 456),
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views._send_invite_notification",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views._persist_invite",
        new_callable=AsyncMock,
        return_value="created",
    ):

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/auth/social/friend_invite",
            SuccessMessages.FRIEND_INVITES_SENT.format(1),
            payload=payload,
            headers=headers,
        )
