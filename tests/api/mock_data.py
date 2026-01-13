from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List

USER_ID = uuid.UUID("131dd20e-d0ee-486d-80e1-a6aa928b0c8e")
REQUEST_ID = uuid.UUID("6324cdb7-e59b-4edf-bda6-9ffd9ee5a7ed")


class MockColumn:
    """Helper to mock a SQLAlchemy column."""

    def __init__(self, key: str) -> None:
        self.key = key


class MockTable:
    """Helper to mock a SQLAlchemy table."""

    def __init__(self, columns: List[str]) -> None:
        self.columns = [MockColumn(c) for c in columns]


class MockModel:
    """Base class for mock models."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.__table__ = MockTable(list(kwargs))

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "__table__"}


def mock_user(
    user_id: uuid.UUID = USER_ID,
    email: str = "test@example.com",
) -> MockModel:
    """Return a mock ORM-like user object."""
    return MockModel(
        id=user_id,
        email=email,
        mobile="1234567890",
        calling_code="+1",
        is_password_set=True,
        password="hashed_password",  # noqa: S106
        state="active",
        is_email_verified=True,
        is_mobile_verified=True,
        login_type=None,
        type="regular",
        login_count=1,
        created_at=datetime.now(timezone.utc),
        modified_at=datetime.now(timezone.utc),
    )


def mock_user_profile(user_id: uuid.UUID = USER_ID, **kwargs: Any) -> MockModel:
    """Return a mock ORM-like user profile object."""
    profile_data = {
        "uuid": user_id,
        "name": "Test User",
        "firstname": "Test",
        "lastname": "User",
        "country_code": "US",
        "gender": "Male",
        "about_me": "I am a test user.",
        "birth_date": date(1990, 1, 1),
        "avatar_id": 1,
        "nick_name": "tester",
        "image_url": "http://example.com/avatar.jpg",
        "created_at": datetime.now(timezone.utc),
        "modified_at": datetime.now(timezone.utc),
    }
    profile_data.update(kwargs)
    return MockModel(**profile_data)


def mock_device(
    user_id: uuid.UUID = USER_ID,
    device_id: str = "device-123",
) -> MockModel:
    """Return a mock ORM-like device object."""
    return MockModel(
        id=uuid.uuid4(),
        device_id=device_id,
        user_id=user_id,
        device_name="Test Phone",
        platform="android",
        device_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def mock_auth_session(
    user_id: uuid.UUID = USER_ID,
    device_id: str = "device-123",
) -> MockModel:
    """Return a mock ORM-like authentication session object."""
    return MockModel(
        id=uuid.uuid4(),
        user_uuid=user_id,
        auth_token="mock_auth_token",  # noqa: S106
        auth_token_expiry=datetime.now(timezone.utc),
        device_id=device_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
