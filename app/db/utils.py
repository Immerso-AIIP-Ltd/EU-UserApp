import asyncio
import enum
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Optional, Sequence, Type

from loguru import logger
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text
from sqlalchemy.engine import RowMapping, make_url
from sqlalchemy.exc import (
    DataError,
    DBAPIError,
    IntegrityError,
    OperationalError,
)
from sqlalchemy.exc import (
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.sql import Executable
from sqlalchemy.sql.elements import TextClause

from app.core.exceptions.exceptions import (
    DBConnectionError,
    DBDataError,
    DBIntegrityError,
    DBOperationalError,
    DBQueryExecutionError,
    DBTimeoutError,
    ValidationError,
)
from app.db.factory import DatabaseFactory
from app.settings import settings

class IntentEnum(enum.Enum):
    """Intent options for OTP verification."""

    REGISTRATION = "registration"
    JOIN_WAITLIST = "joinwaitlist"
    UPDATE_PROFILE = "update_profile"

class PlatformEnum(enum.Enum):
    """Platform options."""

    ANDROID = "android"
    IOS = "ios"
    WEB = "web"

class GenderEnum(enum.Enum):
    """Gender options."""

    MALE = "M"
    FEMALE = "F"
    OTHER = "O"

class SocialProviderEnum(enum.Enum):
    """Social login provider options."""

    GOOGLE = "google"
    APPLE = "apple"
    FACEBOOK = "facebook"
    
@asynccontextmanager
async def get_celery_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for Celery tasks.

    This is a simplified context manager for use in Celery tasks where
    FastAPI's dependency injection is not available.

    Creates a new database factory for each task to ensure connections
    are bound to the current event loop. This is necessary because
    Celery tasks may run in new event loops (e.g. via asyncio.run or new_event_loop),
    and asyncpg connections cannot be shared across loops.

    Usage:
        async with get_celery_db_session() as db:
            # Use db session here
            await db.execute(...)

    Yields:
        AsyncSession: Database session with automatic commit/rollback/close
    """
    # Create a new factory (and engine) for this task/loop
    db_factory = DatabaseFactory(
        db_url=str(settings.db_url),
        db_echo=settings.db_echo,
    )
    db_session = db_factory.get_session()

    try:
        yield db_session
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        raise
    finally:
        await db_session.close()
        # Dispose engine to close connections and clean up
        await db_factory.close()


async def create_database() -> None:
    """Create a database."""
    db_url = make_url(str(settings.db_url_pytest.with_path("/postgres")))
    engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")

    try:
        async with engine.connect() as conn:
            database_existance = await conn.execute(
                text(
                    f"SELECT 1 FROM pg_database WHERE datname='{settings.db_base}_test'",  # noqa: E501,S608
                ),
            )
            database_exists = database_existance.scalar() == 1

        if database_exists:
            await drop_database()

        async with engine.connect() as conn:
            await conn.execute(
                text(
                    f'CREATE DATABASE "{settings.db_base}_test" ENCODING "utf8" TEMPLATE template1',  # noqa: E501
                ),
            )
    finally:
        await engine.dispose()


async def drop_database() -> None:
    """Drop current database."""
    db_url = make_url(str(settings.db_url_pytest.with_path("/postgres")))
    engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            disc_users = (
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE pid <> pg_backend_pid();"
            )
            await conn.execute(text(disc_users))
            await conn.execute(text(f'DROP DATABASE "{settings.db_base}_test"'))
    finally:
        await engine.dispose()


async def execute_query(
    query: Executable,
    params: dict[str, Any],
    db_session: AsyncSession,
    timeout_seconds: Optional[float] = None,
) -> Sequence[RowMapping]:
    """Execute database query.

    Args:
        query: SQL query to execute
        params: Query parameters
        db_session: Database session
        timeout_seconds: Optional query timeout in seconds

    Returns:
        Sequence of row mappings

    Raises:
        DBTimeoutError: Query exceeded timeout
        DBIntegrityError: Integrity constraint violated
        DBDataError: Invalid data type or value
        DBOperationalError: Database operational error
        DBConnectionError: Database connection failed
        DBQueryExecutionError: Other query execution errors
    """
    try:
        if timeout_seconds:
            await db_session.execute(
                text(f"SET LOCAL statement_timeout = '{int(timeout_seconds * 1000)}'"),
            )

        logger.debug(f"Executing query with params: {params}")
        result = await asyncio.wait_for(
            db_session.execute(query, params),
            timeout=timeout_seconds,
        )
        rows = result.mappings().all()
        logger.debug(f"Query returned {len(rows)} rows")
        return rows

    except SQLAlchemyTimeoutError as e:
        error_msg = f"Query timeout after {timeout_seconds}s: {e!s}"
        logger.error(error_msg)
        raise DBTimeoutError(detail=error_msg) from e

    except IntegrityError as e:
        error_msg = f"Integrity constraint violated: {e!s}"
        logger.error(error_msg)
        raise DBIntegrityError(detail=error_msg) from e

    except DataError as e:
        error_msg = f"Invalid data: {e!s}"
        logger.error(error_msg)
        raise DBDataError(detail=error_msg) from e

    except OperationalError as e:
        error_msg = f"Database operational error: {e!s}"
        logger.error(error_msg)
        # Check if it's a connection issue
        if "connection" in str(e).lower() or "connect" in str(e).lower():
            raise DBConnectionError(detail=error_msg) from e
        raise DBOperationalError(detail=error_msg) from e

    except DBAPIError as e:
        error_msg = f"Database API error: {e!s}"
        logger.error(error_msg)
        raise DBQueryExecutionError(detail=error_msg) from e

    except Exception as e:
        error_msg = f"Other query execution error: {e}"
        logger.error(error_msg)
        raise DBConnectionError(detail=error_msg) from e


async def execute_and_transform(
    query: TextClause,
    params: dict[str, Any],
    model_class: Type[BaseModel],
    db_session: AsyncSession,
    timeout_seconds: Optional[float] = None,
) -> List[dict[str, Any]]:
    """Execute query and transform rows to dictionaries.

    Args:
        query: SQL query to execute
        params: Query parameters
        model_class: Pydantic model class for validation
        db_session: Database session
        timeout_seconds: Optional query timeout in seconds

    Returns:
        List of validated dictionaries

    Raises:
        ValidationError: Pydantic validation failed
        DBTimeoutError: Query exceeded timeout
        DBIntegrityError: Integrity constraint violated
        DBDataError: Invalid data type or value
        DBOperationalError: Database operational error
        DBConnectionError: Database connection failed
        DBQueryExecutionError: Other query execution errors
    """
    step_start = time.perf_counter()
    rows = await execute_query(query, params, db_session, timeout_seconds)
    print('rrrrrrrrrr', rows)
    logger.info(f"Step 3.1: Execute query took {time.perf_counter() - step_start:.4f}s")
    step_start = time.perf_counter()
    try:
        validated_data = [
            model_class.model_validate(dict(row)).model_dump(mode="json")
            for row in rows
        ]
        logger.debug(f"Transformed {len(validated_data)} rows")
        logger.info(
            f"Step 3.2: Transform (VALIDATION) rows took {time.perf_counter() - step_start:.4f}s",  # noqa: E501
        )
    except PydanticValidationError as e:
        error_msg = f"Data validation failed: {e!s}"
        logger.error(error_msg)
        raise ValidationError(detail=error_msg) from e

    return validated_data