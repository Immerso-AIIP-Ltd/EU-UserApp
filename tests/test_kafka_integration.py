from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request

from app.api.v1.schemas import UpdateProfileRequest, UserProfileData
from app.api.v1.user_profile.views import update_user_profile


@pytest.mark.asyncio
@patch("app.api.v1.user_profile.views.execute_and_transform")
@patch(
    "app.utils.kafka_producer.KafkaProducerService.publish_event",
    new_callable=AsyncMock,
)
@patch("app.api.v1.user_profile.views.get_user_from_x_token")
@patch("app.api.v1.user_profile.views.standard_response")
async def test_update_user_profile_triggers_kafka(
    mock_standard_response: Any,
    mock_get_user: Any,
    mock_publish: AsyncMock,
    mock_execute: Any,
) -> None:
    # Mock dependencies
    mock_request = AsyncMock(spec=Request)
    mock_profile_update = UpdateProfileRequest(name="John Doe")
    mock_db_session = AsyncMock()
    mock_headers = {}
    mock_cache = AsyncMock()
    mock_current_user = {"uuid": "12345"}

    # Mock execute_and_transform to return a user profile
    mock_user_profile = UserProfileData(uuid="12345", name="John Doe")
    mock_execute.return_value = [mock_user_profile.model_dump(mode="json")]
    mock_get_user.return_value = mock_current_user

    await update_user_profile(
        request=mock_request,
        profile_update=mock_profile_update,
        db_session=mock_db_session,
        headers=mock_headers,
        cache=mock_cache,
        current_user=mock_current_user,
    )

    # Verify Kafka was called
    mock_publish.assert_called_once()
    args, kwargs = mock_publish.call_args
    assert kwargs["event_type"] == "USER_UPDATED"
    assert kwargs["data"]["name"] == "John Doe"
    assert kwargs["data"]["uuid"] == "12345"
