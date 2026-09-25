"""Async engine and session factory. Connections are opened lazily on first use."""

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Database:
    def __init__(self, url: URL, *, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url, echo=echo, pool_pre_ping=True, pool_size=5, max_overflow=10
        )
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def dispose(self) -> None:
        await self.engine.dispose()


__all__ = ["AsyncSession", "Database"]
