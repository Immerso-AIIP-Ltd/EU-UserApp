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
    device_id = "131dd20e-d0ee-486d-80e1-a6aa928b0c8e"
    mock_decrypted = {
        "device_id": device_id,
        "email_id": "waitlist@example.com",
        "name": "Waitlist User",
    }
    payload = {"key": "k", "data": "d"}

    headers = get_auth_headers(device_id=device_id)
    with patch(
        "app.api.v1.friend_invite_joinwaitlist.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views.execute_query",
        new_callable=AsyncMock,
    ) as mock_exec, patch(
        "app.api.v1.friend_invite_joinwaitlist.views.GenerateOtpService.generate_otp",
        new_callable=AsyncMock,
    ):

        # Mock for 4 remaining calls:
        # 1. GET_WAITLIST_BY_DEVICE (_process_email_flow line 176)
        # 2. GET_WAITLIST_BY_EMAIL (_process_email_flow line 224)
        # 3. INSERT_WAITLIST_ENTRY (_process_email_flow line 267)
        # 4. UPSERT_DEVICE_INVITE (_process_email_flow line 280)
        mock_exec.side_effect = [
            [],  # Call 1
            [],  # Call 2
            [
                MockModel(id="sync-id", queue_number=123, is_verified=False),
            ],  # Call 3
            [{"id": "invite-id"}],  # Call 4
        ]

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/social/waitlist",
            SuccessMessages.WAITLIST_OTP_SENT.format("email"),
            payload=payload,
            headers=headers,
        )

        # Verify ID sync
        upsert_call = mock_exec.call_args_list[3]
        assert upsert_call.kwargs["params"]["id"] == "sync-id"


@pytest.mark.anyio
async def test_join_waitlist_duplicate_device(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "device_id": "131dd20e-d0ee-486d-80e1-a6aa928b0c8e",
        "email": "new_email@example.com",
        "name": "New User",
    }
    payload = {"key": "k", "data": "d"}
    headers = get_auth_headers(device_id="test_device")

    with patch(
        "app.api.v1.friend_invite_joinwaitlist.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views.execute_query",
        new_callable=AsyncMock,
    ) as mock_exec:

        # Mock: 1. existing device with DIFFERENT email
        mock_exec.side_effect = [
            [MockModel(email="old_email@example.com")],  # Call 1: waitlist entry
        ]

        response = await client.post(
            "/user/v1/social/waitlist",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 409
        json_data = response.json()
        assert json_data["error"]["error_code"] == "US049"
        assert "different email or mobile number" in json_data["error"]["message"]


@pytest.mark.anyio
async def test_join_waitlist_device_not_registered(
    client: AsyncClient,
    dbsession: AsyncSession,
) -> None:
    mock_decrypted = {
        "device_id": "231dd20e-d0ee-486d-80e1-a6aa928b0c8e",
        "email": "user@example.com",
    }
    payload = {"key": "k", "data": "d"}
    headers = get_auth_headers(device_id="unregistered_device")

    with patch(
        "app.api.v1.friend_invite_joinwaitlist.views.SecurityService.decrypt_payload",
        return_value=mock_decrypted,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views.DeviceService.is_device_registered",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views.execute_query",
        new_callable=AsyncMock,
    ):

        # Call the endpoint

        response = await client.post(
            "/user/v1/social/waitlist",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 404
        json_data = response.json()
        assert json_data["error"]["error_code"] == "US404"
        assert "Device not registered" in json_data["error"]["message"]


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
    headers = get_auth_headers(
        device_id="test_device",
        token="test_token",  # noqa: S106
    )

    mock_waitlist_entry = MockModel(
        id=123,
        email="inviter@example.com",
        queue_number=123,
    )

    with patch(
        "app.api.v1.friend_invite_joinwaitlist.views._resolve_inviter",
        new_callable=AsyncMock,
        return_value=(mock_waitlist_entry, 456),
    ), patch(
        "app.api.v1.friend_invite_joinwaitlist.views._check_if_already_member",
        new_callable=AsyncMock,
        return_value=False,
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
            "/user/v1/social/friend_invite",
            SuccessMessages.FRIEND_INVITES_SENT.format(1),
            payload=payload,
            headers=headers,
        )
