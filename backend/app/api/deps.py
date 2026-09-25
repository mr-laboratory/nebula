"""FastAPI dependencies: a per-request DB session (unit of work) and the shared Redis client."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.db.session import AsyncSession, Database


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Commit if the handler succeeds, roll back if it raises."""
    db = cast(Database, request.app.state.db)
    async with db.sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


# scope="function": commit before the response is sent, so a failed commit is never reported as OK.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
RedisDep = Annotated[Redis, Depends(get_redis)]
