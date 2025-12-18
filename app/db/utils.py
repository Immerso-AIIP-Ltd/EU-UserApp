from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.settings import settings


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
 