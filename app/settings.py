import enum
from pathlib import Path
from tempfile import gettempdir
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL

TEMP_DIR = Path(gettempdir())


class LogLevel(str, enum.Enum):
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    workers_count: int = Field(default=4)
    reload: bool = Field(default=False)
    debug: bool = Field(default=False)
    log_dir: Path = Field(default=TEMP_DIR / "logs")
    environment: str = Field(default="dev")
    log_level: LogLevel = Field(default=LogLevel.INFO)

    # api version
    api_version: str = Field(default="v1")

    # Variables for the database
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_user: str = Field(default="app")
    db_pass: str = Field(default="app")
    db_base: str = Field(default="admin")
    db_echo: bool = Field(default=False)
    db_pool_size: int = Field(default=100)
    db_max_overflow: int = Field(default=50)

    # Variables for Redis
    redis_pass: Optional[str] = Field(default=None)
    redis_cluster_nodes: Optional[str] = Field(default=None)
    redis_socket_timeout: int = Field(default=5)

    # Variables for OAuth Redis
    oauth_redis_pass: Optional[str] = Field(default=None)
    oauth_redis_cluster_nodes: Optional[str] = Field(default=None)
    oauth_redis_socket_timeout: int = Field(default=5)

    # JWT Settings
    jwt_secret_key: str = Field(
        default="this-is-a-very-secure-and-long-secret-key-for-testing-purposes",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=14400)
    user_token_days_to_expire: int = Field(default=30)

    # Celery settings
    celery_broker_url: Optional[str] = Field(default=None)
    celery_backend_url: Optional[str] = Field(default=None)

    # Register block timeout
    block_duration_seconds: str = Field(default="60")
    brevo_forgot_password_template_id: str = Field(default="dummy")
    brevo_registration_success_template_id: str = Field(default="dummy")
    brevo_email_verification_template_id: str = Field(default="dummy")
    brevo_otp_resend_template_id: str = Field(default="dummy")
    brevo_password_change_success_template_id: str = Field(default="dummy")
    brevo_profile_update_success_template_id: str = Field(default="dummy")
    sms_friend_invite_template_id: str = Field(default="695f8c33374e046e72677aeb")
    msg91_sender_id: str = Field(default="EROSNV")
    msg91_entity_id: str = Field(default="1107176786435257801")
    erosuniverse_website_url: str = Field(default="https://example.com")
    brevo_reset_url: str = Field(default="https://example.com/reset")

    # Communication Service settings
    comm_service_x_api_client: str = Field(default="dummy")
    comm_service_x_service_token: str = Field(default="dummy")
    communication_api_url: str = Field(default="https://example.com")
    web_url: str = Field(default="https://example.com")

    # Legacy API settings
    legacy_api_url: str = Field(default="https://example.com")
    legacy_oauth_consumer_key: str = Field(default="dummy")
    legacy_oauth_consumer_secret: str = Field(default="dummy")

    google_client_id: str = Field(default="dummy")
    google_android_client_id: str = Field(default="dummy")
    google_ios_client_id: str = Field(default="dummy")
    google_web_client_id: str = Field(default="dummy")

    apple_client_id: str = Field(default="dummy")
    apple_ios_client_id: str = Field(default="dummy")
    apple_team_id: str = Field(default="dummy")
    apple_key_id: str = Field(default="dummy")
    apple_private_key: str = Field(default="dummy")
    apple_public_key_url: str = Field(default="https://appleid.apple.com/auth/keys")
    apple_issuer: str = Field(default="https://appleid.apple.com")

    facebook_client_id: str = Field(default="dummy")
    facebook_client_secret: str = Field(default="dummy")

    # FusionAuth Settings
    fusionauth_url: str = Field(default="http://localhost:9011")
    fusionauth_api_key: str = Field(default="dummy")
    fusionauth_client_id: str = Field(default="dummy")
    fusionauth_bootstrap_key_id: Optional[str] = Field(default=None)
    decryption_private_key_b64: Optional[str] = Field(default=None)

    # ReCaptcha Settings
    recaptcha_project_id: str = Field(default="eros-universe-8cddf")

    # Kafka Settings
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_topic_user_profile: str = Field(default="user_profile_event")

    # Other settings
    CACHE_TIMEOUT_FOR_EMAIL_DNS: int = Field(default=300)
    skip_partner_auth_redis_check: list[str] = Field(default=[])
    token_leeway_threshold_in_days: int = Field(default=15)
    load_test_bypass_secret: str = Field(default="dummy")

    # Deep Links
    deeplink_login_screen: str = Field(default="dummy")
    deeplink_otp_screen: str = Field(default="dummy")
    deeplink_set_password: str = Field(default="dummy")
    deeplink_link_account: str = Field(default="dummy")
    facebook_auth_link: str = Field(default="dummy")

    # Reward API Settings
    reward_api_url: str = Field(default="https://example.com")

    # FREE plan Service Settings
    app_assign_free_plan_api_url: str = Field(
        default="http://dev-apigateway.erosuniverse.com",
    )
    app_assign_free_plan_public_key: str = Field(default="dummy")

    @property
    def db_url(self) -> URL:
        """
        Assemble database URL from settings.

        :return: database URL.
        """
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_base}",
        )

    @property
    def db_url_pytest(self) -> URL:
        """
        Assemble database URL from settings for pytest.

        :return: database URL.
        """
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_base}_test",
        )

    @property
    def celery_broker_url_computed(self) -> str:
        """Assemble Celery broker URL from settings.

        Uses explicit celery_broker_url if set.

        :return: Celery broker URL.
        """
        if self.celery_broker_url:
            return self.celery_broker_url
        return ""

    @property
    def celery_backend_url_computed(self) -> str:
        """Assemble Celery result backend URL from settings.

        Uses explicit celery_backend_url if set.

        :return: Celery backend URL.
        """
        if self.celery_backend_url:
            return self.celery_backend_url
        return ""

    @property
    def verify_otp_url(self) -> str:
        """URL for verifying OTP via Communication Service."""
        return f"{self.communication_api_url}/api/v1/comm/otp/validate/"

    @property
    def generate_otp_url(self) -> str:
        """URL for generating OTP via Communication Service."""
        return f"{self.communication_api_url}/api/v1/comm/otp/generate/"

    @property
    def mail_send_url(self) -> str:
        """URL for sending emails via Communication Service."""
        return f"{self.communication_api_url}/api/v1/comm/email/send/"

    @property
    def sms_send_url(self) -> str:
        """URL for sending SMS via Communication Service."""
        return f"{self.communication_api_url}/api/v1/comm/sms/send/"

    @property
    def mobile_verify_url(self) -> str:
        """URL for mobile number verification via Communication Service."""
        return f"{self.communication_api_url}/api/v1/comm/sms/verify_mobile/"

    @property
    def legacy_login_url(self) -> str:
        """URL for legacy API login."""
        return f"{self.legacy_api_url}/api/v2/secured/user/login"

    @property
    def legacy_logout_url(self) -> str:
        """URL for legacy API logout."""
        return f"{self.legacy_api_url}/api/v2/secured/user/logout"

    @property
    def legacy_map_gcm_url(self) -> str:
        """URL for mapping GCM tokens in legacy API."""
        return f"{self.legacy_api_url}/api/v2/secured/user/mapgcm"

    @property
    def asset_commit_url(self) -> str:
        """URL for asset commit via Asset Manager."""
        return f"{self.communication_api_url}/asset/v1/asset-manager/commit"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]
