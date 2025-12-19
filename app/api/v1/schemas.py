from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.constants import Description, SuccessMessages


class CacheStats(BaseModel):
    """
    Schema for Redis cache statistics.
    """

    used_memory_human: Optional[str] = None
    connected_clients: Optional[Any] = None
    total_commands_processed: Optional[Any] = None
    uptime_in_days: Optional[Any] = None
    total_keys: int
    keys: List[str]


# ==================== ENUMS ====================


class SortOrder(str, Enum):
    """Sort order options."""

    ASC = "asc"
    DESC = "desc"


class SortBy(str, Enum):
    """Sort by field options."""

    RANK = "rank"
    NAME = "name"
    CREATED_AT = "created_at"


class IntentEnum(str, Enum):
    """Intent options for OTP verification."""

    REGISTRATION = "registration"
    JOIN_WAITLIST = "joinwaitlist"
    UPDATE_PROFILE = "update_profile"


class PlatformEnum(str, Enum):
    """Platform options."""

    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class GenderEnum(str, Enum):
    """Gender options."""

    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class SocialProviderEnum(str, Enum):
    """Social login provider options."""

    GOOGLE = "google"
    APPLE = "apple"
    FACEBOOK = "facebook"


# ==================== REQUEST SCHEMAS ====================


class DeviceInviteStatusRequest(BaseModel):
    """Request schema for /user/v1/device/invite-status."""

    device_id: str = Field(..., description=Description.DEVICE_ID)


class DeviceInviteRequest(BaseModel):
    """Request schema for /user/v1/device/invite."""

    device_id: str = Field(..., description=Description.DEVICE_ID)
    coupon_id: str = Field(..., description=Description.COUPON_ID)


class LoginRequest(BaseModel):
    """Request schema for /user/v1/user/login."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )
    password: Optional[str] = Field(default=None, description=Description.PASSWORD)

    @model_validator(mode="after")
    def validate_login_credentials(self):
        """Validate that either email or mobile+calling_code is provided."""
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email or mobile with calling_code must be provided.",
            )
        return self


class RegisterWithProfileRequest(BaseModel):
    """Request schema for /user/v1/user/register_with_profile."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )
    password: str = Field(..., description=Description.PASSWORD)
    name: Optional[str] = Field(default=None, description=Description.NAME)
    avatar_id: Optional[int] = Field(default=None, description=Description.AVATAR_ID)
    birth_date: Optional[date] = Field(default=None, description=Description.BIRTH_DATE)
    profile_image: Optional[str] = Field(
        default=None, description=Description.PROFILE_IMAGE,
    )

    @model_validator(mode="after")
    def validate_contact_info(self):
        """Validate that either email or mobile+calling_code is provided."""
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email or mobile with calling_code must be provided.",
            )
        return self


class VerifyOTPRequest(BaseModel):
    """Request schema for OTP verification endpoints."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )
    otp: str = Field(..., description=Description.OTP)
    intent: IntentEnum = Field(..., description=Description.INTENT)

    @model_validator(mode="after")
    def validate_contact_info(self):
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email or mobile with calling_code must be provided.",
            )
        return self


class VerifyOTPRegisterRequest(BaseModel):
    """Request schema for /user/v1/user/verify_otp_register."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )
    otp: str = Field(..., description=Description.OTP)
    password: str = Field(..., description=Description.PASSWORD)
    intent: IntentEnum = Field(
        default=IntentEnum.REGISTRATION, description=Description.INTENT,
    )

    @model_validator(mode="after")
    def validate_contact_info(self):
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email or mobile with calling_code must be provided.",
            )
        return self


class ResendOTPRequest(BaseModel):
    """Request schema for resending OTP."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )
    intent: IntentEnum = Field(..., description=Description.INTENT)

    @model_validator(mode="after")
    def validate_contact_info(self):
        """Validate that either email or mobile+calling_code is provided."""
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email or mobile with calling_code must be provided.",
            )
        return self


class ForgotPasswordRequest(BaseModel):
    """Request schema for /user/v1/user/forgot_password."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )

    @model_validator(mode="after")
    def validate_contact_info(self):
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email or mobile with calling_code must be provided.",
            )
        return self


class ChangePasswordRequest(BaseModel):
    """Request schema for /user/v1/user/change_password."""

    new_password: str = Field(..., description=Description.NEW_PASSWORD)


class UpdateProfileRequest(BaseModel):
    """Request schema for /user/v1/user/profile PUT."""

    name: Optional[str] = Field(default=None, description=Description.NAME)
    gender: Optional[GenderEnum] = Field(default=None, description=Description.GENDER)
    about_me: Optional[str] = Field(default=None, description=Description.ABOUT_ME)
    birth_date: Optional[str] = Field(default=None, description=Description.BIRTH_DATE)
    nick_name: Optional[str] = Field(default=None, description=Description.NICK_NAME)
    country: Optional[str] = Field(default=None, description=Description.COUNTRY)
    avatar_id: Optional[int] = Field(default=None, description=Description.AVATAR_ID)
    profile_image: Optional[str] = Field(
        default=None, description=Description.PROFILE_IMAGE,
    )


class UpdateEmailMobileRequest(BaseModel):
    """Request schema for /user/v1/user/update_email_mobile."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )

    @model_validator(mode="after")
    def validate_one_field(self):
        if self.email and (self.mobile or self.calling_code):
            raise ValueError("Provide only one contact method (email OR mobile).")
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email or mobile with calling_code must be provided.",
            )
        return self


class WaitlistRequest(BaseModel):
    """Request schema for /user/v1/social/waitlist."""

    device_id: str = Field(..., description=Description.DEVICE_ID)
    email_id: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )

    @model_validator(mode="after")
    def validate_contact_info(self):
        if not self.email_id and not (self.mobile and self.calling_code):
            raise ValueError(
                "Either email_id or mobile with calling_code must be provided.",
            )
        return self


class FriendInviteObject(BaseModel):
    """Object schema for friend invite item containing email or mobile details."""

    email: Optional[EmailStr] = Field(default=None, description=Description.EMAIL)
    mobile: Optional[str] = Field(default=None, description=Description.MOBILE)
    calling_code: Optional[str] = Field(
        default=None, description=Description.CALLING_CODE,
    )

    @model_validator(mode="after")
    def validate_contact_info(self):
        """Ensure either email or mobile+calling_code is present."""
        if not self.email and not (self.mobile and self.calling_code):
            raise ValueError("Either email or mobile with calling_code is required.")
        return self


# Item can be a simple email string or the object details
FriendInviteItem = Union[EmailStr, FriendInviteObject]


class FriendInviteRequest(BaseModel):
    """Request schema for /user/v1/social/friend-invite."""

    invited_list: List[FriendInviteItem] = Field(
        ..., description=Description.INVITED_LIST,
    )

    @model_validator(mode="after")
    def validate_list(self):
        if not self.invited_list:
            raise ValueError("invited_list cannot be empty.")
        return self


class SocialLoginRequest(BaseModel):
    """Request schema for social login (Google/Apple/Facebook)."""

    user_id: str = Field(..., description=Description.SOCIAL_USER_ID)
    token: str = Field(..., description=Description.OAUTH_TOKEN)


# ==================== RESPONSE SCHEMAS ====================


class GenericResponse(BaseModel):
    """Generic response schema matching /components/schemas/GenericResponse."""

    status: Union[bool, str] = Field(..., description=SuccessMessages.SUCCESS)
    message: Optional[str] = Field(default=None, description=SuccessMessages.MESSAGE)
    data: Optional[Dict[str, Any]] = Field(
        default=None, description=SuccessMessages.DATA,
    )


class UserProfileData(BaseModel):
    """Data schema for User Profile."""

    uuid: str
    email: Optional[str] = None
    name: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    mobile: Optional[str] = None
    calling_code: Optional[Union[str, int]] = None
    image: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None
    about_me: Optional[str] = None
    birth_day: Optional[str] = None
    birth_month: Optional[str] = None
    birth_year: Optional[Union[int, str]] = None
    avatar_id: Optional[int] = None
    is_password_set: Optional[bool] = None
    nick_name: Optional[str] = None
    birth_date: Optional[Union[str, date]] = None
    identity_providers: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AuthTokenData(BaseModel):
    """Data schema for Auth Token response."""

    auth_token: str
    token: Optional[str] = None
    token_secret: Optional[str] = None
    auth_token_expiry: Optional[int] = None
    user: Optional[Dict[str, Any]] = None  # Or partial user profile


class LoginResponse(GenericResponse):
    """Response schema for Login."""

    data: AuthTokenData


class UserProfileResponse(GenericResponse):
    """Response schema for Get/Update Profile."""

    data: UserProfileData


class DeviceInviteData(BaseModel):
    device_id: str
    user_id: Optional[str] = None
    device_name: Optional[str] = None
    invited: Optional[bool] = False
    message: Optional[str] = ""


class DeviceInviteResponse(GenericResponse):
    """Response schema for Device Invite."""

    data: DeviceInviteData


class WaitlistData(BaseModel):
    queue_number: Optional[int] = None
    is_verified: Optional[bool] = None
    status: Optional[str] = None


class WaitlistResponse(GenericResponse):
    """Response schema for Waitlist."""

    data: WaitlistData


class FriendInviteData(BaseModel):
    invited: List[Any] = []
    duplicates: List[Any] = []
    invalid: List[Any] = []
    failed: List[Any] = []


class FriendInviteResponse(GenericResponse):
    """Response schema for Friend Invite."""

    data: FriendInviteData


class SocialLoginResponse(GenericResponse):
    """Response schema for Social Login."""

    data: AuthTokenData
