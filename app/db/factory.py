"""Database factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class DatabaseFactory:
    """Database factory."""

    def __init__(self, db_url: str, db_echo: bool) -> None:
        self.engine = create_async_engine(db_url, echo=db_echo)
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

    def get_session(self) -> AsyncSession:
        """Get session."""
        return self.session_factory()

    async def close(self) -> None:
        """Close connection."""
        await self.engine.dispose()
