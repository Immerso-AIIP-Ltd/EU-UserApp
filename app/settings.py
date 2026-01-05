import enum
from pathlib import Path
from tempfile import gettempdir
from typing import Optional
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
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

    host: str = "127.0.0.1"
    port: int = 8000
    # quantity of workers for uvicorn
    workers_count: int = 1
    # Enable uvicorn reloading
    reload: bool = False

    # Enable debug mode
    debug: bool = False

    # Log directory
    log_dir: Path = TEMP_DIR / "logs"

    # Current environment
    environment: str = "dev"

    # Log level
    log_level: LogLevel = LogLevel.INFO

    # api version
    api_version: str = "v1"

    # Variables for the database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "app"
    db_pass: str = "app"
    db_base: str = "admin"
    db_echo: bool = False

    # Variables for Redis
    redis_host: str = "app-redis"
    redis_port: int = 6379
    redis_user: Optional[str] = None
    redis_pass: Optional[str] = None
    redis_base: Optional[int] = None

    # JWT Settings
    jwt_secret_key: str = "your-secret-key"  # Should be set via environment variable
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    user_token_days_to_expire: int = 90

    # Celery settings
    celery_broker_url: Optional[str] = None
    celery_backend_url: Optional[str] = None

    # Register block timeout
    block_duration_seconds: str = "240000"
    brevo_forgot_password_template_id: str = "8"
    brevo_registration_success_template_id: str = "9"
    brevo_email_verification_template_id: str = "10"
    brevo_otp_resend_template_id: str = "11"
    brevo_password_change_success_template_id: str = "14"
    brevo_profile_update_success_template_id: str = "15"
    erosuniverse_website_url: str = "https://dev.erosuniverse.com/"
    brevo_reset_url: str = "https://dev.erosuniverse.com/forgotPwd"
    forgot_mobile_password_response: str = "OTP sent you successfully"

    # Communication Service settings
    comm_service_x_api_client: str = "CZgbPYnmcj5iyEH9tg0GYvB4lm9gGQ9qs6jQwllV"
    comm_service_x_service_token: str = (
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.e30.TWUdmzGEToMw7xpFthorSm9Os5qdl-SU0XAg3qGLRM4"
    )
    communication_api_url: str = "https://dev-apigateway.erosuniverse.com"
    web_url: str = "https://dev.erosuniverse.com/"

    # Legacy API settings
    legacy_api_url: str = "https://dev-apigateway.erosuniverse.com"
    legacy_oauth_consumer_key: str = "4e297e55a0600bb031c03b579f3151d3050220d41"
    legacy_oauth_consumer_secret: str = "8fadbc16ca36f3d2165a33f43be07411"

    # Google Social Login Settings
    google_client_id: str = "YOUR_GOOGLE_CLIENT_ID"
    google_android_client_id: str = "YOUR_GOOGLE_ANDROID_CLIENT_ID"
    google_ios_client_id: str = "YOUR_GOOGLE_IOS_CLIENT_ID"

    # Apple Social Login Settings
    apple_client_id: str = "YOUR_APPLE_CLIENT_ID"
    apple_ios_client_id: str = "YOUR_APPLE_IOS_CLIENT_ID" 
    apple_team_id: str = "YOUR_APPLE_TEAM_ID"
    apple_key_id: str = "YOUR_APPLE_KEY_ID"
    apple_private_key: str = "YOUR_APPLE_PRIVATE_KEY"  # Multiline string recommended to be passed as env var with \n escaped

    # Facebook Social Login Settings
    facebook_client_id: str = "YOUR_FACEBOOK_CLIENT_ID"
    facebook_client_secret: str = "YOUR_FACEBOOK_CLIENT_SECRET"

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
    def redis_url(self) -> URL:
        """
        Assemble REDIS URL from settings.

        :return: redis URL.
        """
        path = ""
        if self.redis_base is not None:
            path = f"/{self.redis_base}"
        return URL.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            user=self.redis_user,
            password=self.redis_pass,
            path=path,
        )

    @property
    def celery_broker_url_computed(self) -> str:
        """Assemble Celery broker URL from settings.

        Uses explicit celery_broker_url if set, otherwise defaults to Redis.

        :return: Celery broker URL.
        """
        if self.celery_broker_url:
            return self.celery_broker_url
        # Use Redis with authentication
        # Build URL with password if provided
        if self.redis_pass:
            auth = (
                f":{self.redis_pass}@"
                if self.redis_user is None
                else f"{self.redis_user}:{self.redis_pass}@"
            )
            base = self.redis_base if self.redis_base is not None else 0
            return f"redis://{auth}{self.redis_host}:{self.redis_port}/{base}"
        # Fallback to no auth
        base = self.redis_base if self.redis_base is not None else 0
        return f"redis://{self.redis_host}:{self.redis_port}/{base}"

    @property
    def celery_backend_url_computed(self) -> str:
        """Assemble Celery result backend URL from settings.

        Uses explicit celery_backend_url if set, otherwise defaults to Redis.

        :return: Celery backend URL.
        """
        if self.celery_backend_url:
            return self.celery_backend_url
        # Use Redis with authentication for backend (can be same or different DB)
        # Build URL with password if provided
        if self.redis_pass:
            auth = (
                f":{self.redis_pass}@"
                if self.redis_user is None
                else f"{self.redis_user}:{self.redis_pass}@"
            )
            base = self.redis_base if self.redis_base is not None else 1
            return f"redis://{auth}{self.redis_host}:{self.redis_port}/{base}"
        # Fallback to no auth
        base = self.redis_base if self.redis_base is not None else 1
        return f"redis://{self.redis_host}:{self.redis_port}/{base}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        env_file_encoding="utf-8",
    )


settings = Settings()
