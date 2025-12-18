import enum
from pathlib import Path
from tempfile import gettempdir
from typing import Optional

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
    db_echo: bool = False

    # Variables for Redis
    redis_host: str = "app-redis"
    redis_port: int = 6379
    redis_user: Optional[str] = None
    redis_pass: Optional[str] = None
    redis_base: Optional[int] = None

    # Celery settings
    celery_broker_url: Optional[str] = None
    celery_backend_url: Optional[str] = None

    def db_url(self, db_name: str = "admin") -> URL:
        """
        Assemble database URL from settings.

        :param db_name: Database name.
        :return: database URL.
        """
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{db_name}",
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
