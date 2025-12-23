# Enums
import enum
import uuid
from datetime import datetime
from datetime import timezone as dt_timezone
from tokenize import String
from typing import ClassVar

from app.db.utils import get_random_string
from sqlalchemy import (
    CHAR,
    UUID,
    VARCHAR,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserState(str, enum.Enum):
    """User account state."""

    inactive = "inactive"
    active = "active"
    blocked = "blocked"
    deactivated = "deactivated"


class UserType(str, enum.Enum):
    """User type."""

    regular = "regular"
    creator = "creator"


class LoginType(str, enum.Enum):
    """Login type."""

    google = "google"
    facebook = "facebook"
    apple = "apple"


class InviteStatus(str, enum.Enum):
    """Friend invite status."""

    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class CouponStatus(str, enum.Enum):
    """Invite coupon status."""

    active = "active"
    used = "used"
    expired = "expired"


class User(Base):
    """Represents the user table."""

    __tablename__ = "user"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(VARCHAR(255), nullable=False, unique=True, index=True)
    mobile = Column(VARCHAR(20), nullable=False)
    calling_code = Column(VARCHAR(10), nullable=False)
    is_password_set = Column(Boolean, default=False)
    password = Column(Text)
    state: Mapped[UserState] = mapped_column(
        Enum(UserState),
        default=UserState.active,
    )
    is_email_verified = Column(Boolean, default=False)
    is_mobile_verified = Column(Boolean, default=False)
    account_locked_until = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    login_type: Mapped[LoginType] = mapped_column(
        Enum(LoginType),
        nullable=True,
    )
    type: Mapped[UserType] = mapped_column(
        Enum(UserType),
        default=UserType.regular,
    )
    login_count = Column(Integer, default=0)
    last_login_at = Column(DateTime(timezone=True))
    deactivated_at = Column(DateTime(timezone=True))
    deactivation_reason = Column(Text)
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        index=True,
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    auth_sessions = relationship("AuthenticationSession", back_populates="user")
    waitlist_entries = relationship("Waitlist", back_populates="user")
    sent_invites = relationship(
        "FriendInvite",
        back_populates="inviter",
        foreign_keys="FriendInvite.inviter_id",
    )
    received_invites = relationship(
        "FriendInvite",
        back_populates="invited_user",
        foreign_keys="FriendInvite.invited_user_id",
    )
    social_identities = relationship("SocialIdentityProvider", back_populates="user")
    devices = relationship("Device", back_populates="user")
    invite_device = relationship("InviteDevice", back_populates="user", uselist=False)


class UserProfile(Base):
    """Represents the user_profile table."""

    __tablename__ = "user_profile"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_app.user.id"),
        primary_key=True,
    )
    firstname = Column(VARCHAR(100))
    lastname = Column(VARCHAR(100))
    country_code = Column(VARCHAR(10))
    gender = Column(CHAR(10))
    about_me = Column(Text)
    birth_date = Column(Date)
    avatar_id = Column(Integer)
    nick_name = Column(VARCHAR(100))
    image_url = Column(Text)
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="profile")


class Platform(Base):
    """Represents the platform table."""

    __tablename__ = "platform"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    platform_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_name = Column(VARCHAR, unique=True, index=True)
    modified_on = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )

    # Relationships
    devices = relationship("Device", back_populates="platform")


class Device(Base):
    """Represents the device table."""

    __tablename__ = "device"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(VARCHAR(255), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_app.user.id"), index=True)
    device_name = Column(VARCHAR(255))
    device_type = Column(VARCHAR(50), index=True)
    platform = Column(
        VARCHAR(20),
        ForeignKey("user_app.platform.platform_name"),
        index=True,
    )
    device_ip = Column(INET, index=True)
    is_vpn = Column(Boolean, default=False, index=True)
    is_anonymous_proxy = Column(Boolean, default=False)
    residency_verified = Column(Boolean, default=False)
    is_rooted = Column(Boolean, default=False, index=True)
    is_jailbroken = Column(Boolean, default=False, index=True)
    device_active = Column(Boolean, default=True)
    drm_type = Column(VARCHAR(50))
    hardware_encryption = Column(Boolean, default=False)
    transaction_type = Column(VARCHAR(50))
    is_ip_legal = Column(Boolean, default=True)
    push_token = Column(Text)
    user_token = Column(Text)
    native_token = Column(Text)
    date_deactivated = Column(DateTime(timezone=True), index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="devices")
    platform_ref = relationship("Platform", back_populates="devices")
    auth_sessions = relationship("AuthenticationSession", back_populates="device")
    waitlist_entry = relationship("Waitlist", back_populates="device", uselist=False)
    invite_device = relationship("InviteDevice", back_populates="device")


class AuthenticationSession(Base):
    """Represents the authentication_session table."""

    __tablename__ = "authentication_session"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_app.user.id"),
        nullable=False,
        index=True,
    )
    auth_token = Column(Text, nullable=False, unique=True, index=True)
    token_secret = Column(Text)
    auth_token_expiry = Column(DateTime(timezone=True), index=True)
    device_id = Column(
        VARCHAR(255),
        ForeignKey("user_app.device.device_id"),
        index=True,
    )
    platform = Column(VARCHAR(20))
    app_version = Column(VARCHAR(20))
    country_code = Column(VARCHAR(10))
    ip_address = Column(INET)
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    logged_out_at = Column(DateTime(timezone=True))
    logout_reason = Column(VARCHAR(50))
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    last_used_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="auth_sessions")
    device = relationship("Device", back_populates="auth_sessions")


class OtpVerification(Base):
    """Represents the otp_verification table."""

    __tablename__ = "otp_verification"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(VARCHAR(255), index=True)
    mobile = Column(VARCHAR(20))
    calling_code = Column(VARCHAR(10))
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        index=True,
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )


class OtpToken(Base):
    """Represents the otp_token table."""

    __tablename__ = "otp_token"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(VARCHAR(255))
    otp = Column(VARCHAR(10), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    expires_at = Column(DateTime(timezone=True))
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )


class Waitlist(Base):
    """Represents the waitlist table."""

    __tablename__ = "waitlist"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_app.user.id"))
    email = Column(VARCHAR(255), nullable=False, index=True)
    mobile = Column(VARCHAR(20), nullable=False)
    calling_code = Column(VARCHAR(10), nullable=False)
    device_id = Column(
        VARCHAR(255),
        ForeignKey("user_app.device.id"),
        unique=True,
        index=True,
    )
    queue_number = Column(Integer, index=True)
    is_verified = Column(Boolean, default=False, index=True)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="waitlist_entries")
    device = relationship("Device", back_populates="waitlist_entry")
    friend_invite = relationship("FriendInvite", back_populates="waitlist")


class FriendInvite(Base):
    """Represents the friend_invite table."""

    __tablename__ = "friend_invite"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inviter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_app.user.id"),
        nullable=False,
        index=True,
    )
    invited_email = Column(VARCHAR(255), nullable=False, index=True)
    invited_mobile = Column(VARCHAR(20), nullable=False)
    invited_calling_code = Column(VARCHAR(10), nullable=False)
    status = Column(VARCHAR(20), default="pending", index=True)
    invite_token = Column(VARCHAR(255), unique=True, index=True)
    invite_sent_at = Column(DateTime(timezone=True))
    invited_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_app.user.id"),
        index=True,
    )
    waitlist_id = Column(UUID(as_uuid=True), ForeignKey("user_app.waitlist.id"))
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    inviter = relationship(
        "User",
        back_populates="sent_invites",
        foreign_keys=[inviter_id],
    )
    invited_user = relationship(
        "User",
        back_populates="received_invites",
        foreign_keys=[invited_user_id],
    )
    waitlist = relationship("Waitlist", back_populates="friend_invite")


class InviteCoupon(Base):
    """Represents the invite_coupon table."""

    __tablename__ = "invite_coupon"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(VARCHAR(255), unique=True)
    status: Mapped[CouponStatus] = mapped_column(
        Enum(CouponStatus),
        default=CouponStatus.active,
    )
    expiry_date = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    invite_devices = relationship("InviteDevice", back_populates="coupon")


class InviteDevice(Base):
    """Represents the invite_device table."""

    __tablename__ = "invite_device"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(
        VARCHAR(255),
        ForeignKey("user_app.device.device_id"),
    )
    coupon_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_app.invite_coupon.id"),
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_app.user.id"),
        unique=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    device = relationship("Device", back_populates="invite_device")
    coupon = relationship("InviteCoupon", back_populates="invite_devices")
    user = relationship("User", back_populates="invite_device")


class SocialIdentityProvider(Base):
    """Represents the social_identity_provider table."""

    __tablename__ = "social_identity_provider"
    __table_args__: ClassVar = {"schema": "user_app"}  # type: ignore[misc]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_app.user.id"),
        nullable=False,
        index=True,
    )
    provider = Column(VARCHAR(50), nullable=False)
    provider_user_id = Column(VARCHAR(255), nullable=False)
    email = Column(VARCHAR(255))
    token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
    )
    modified_at = Column(
        DateTime(timezone=True),
        default=datetime.now(dt_timezone.utc),
        onupdate=datetime.now(dt_timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="social_identities")


class InviteCoupon(Base):
    __tablename__ = "invite_coupon"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid)
    code = Column(String, unique=True, nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)  # track usage
    expires_at = Column(DateTime(timezone=True), nullable=False)


class DeviceInvite(Base):
    __tablename__ = "invite_device"
    device_id = Column(UUID(as_uuid=True), primary_key=True)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("invite_coupon.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class UserAuthToken(Base):
    __tablename__ = "user_auth_token"
    __table_args__: ClassVar = {"schema": "user_app"}

    uuid = Column(UUID(as_uuid=True), primary_key=True)
    token = Column(Text)
    app_consumer_id = Column(UUID(as_uuid=True), ForeignKey("user_app.app_consumer.id"))
    device_id = Column(VARCHAR(128))
    expires_at = Column(DateTime(timezone=True))
    oauth1_token = Column(VARCHAR(128))
    oauth1_token_secret = Column(VARCHAR(128))
    partner_id = Column(VARCHAR(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AppConsumer(Base):
    __tablename__ = "app_consumer"
    __table_args__: ClassVar = {"schema": "user_app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(VARCHAR(128))
    client_id = Column(VARCHAR(40), default=get_random_string)
    client_secret = Column(VARCHAR(40), default=get_random_string)
    description = Column(Text)
    legacy_consumer_key = Column(VARCHAR(128))
    legacy_consumer_secret = Column(VARCHAR(128))
    is_internal = Column(Boolean, default=False)
    partner_code = Column(VARCHAR(40), nullable=True, default='EROS')

    # Relationships
    user_auth_tokens = relationship("UserAuthToken", back_populates="app_consumer")