"""Database factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class DatabaseFactory:
    """Database factory."""

    def __init__(
        self,
        db_url: str,
        db_echo: bool,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        self.engine = create_async_engine(
            db_url,
            echo=db_echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
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
