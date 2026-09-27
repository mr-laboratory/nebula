"""FastAPI dependencies: DB session (unit of work), Redis, settings, current user, permissions."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.logging import user_id_ctx
from app.core.security import decode_access_token
from app.db.session import AsyncSession, Database
from app.models import User
from app.services.permissions import has_permission


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


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


# scope="function": commit before the response is sent, so a failed commit is never reported as OK.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
RedisDep = Annotated[Redis, Depends(get_redis)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]

_bearer = HTTPBearer(auto_error=False, description="Access token from POST /auth/login")


async def get_optional_user(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """The signed-in user, or None for anonymous requests. A bad token is still a 401."""
    if credentials is None:
        return None
    user = await session.get(User, decode_access_token(credentials.credentials, settings))
    if user is None or not user.is_active:
        raise UnauthorizedError("The access token is invalid or has expired.")
    user_id_ctx.set(str(user.id))  # later log lines for this request carry it
    return user


async def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if user is None:
        raise UnauthorizedError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_permission(code: str) -> Callable[..., Awaitable[User]]:
    """A dependency that returns the signed-in user if one of their roles grants `code`.

    Usage: `admin: Annotated[User, Depends(require_permission(USER_MANAGE))]`.
    Anonymous requests get 401, signed-in users without the permission 403.
    """

    async def guard(user: CurrentUser, session: SessionDep) -> User:
        if not await has_permission(session, user.id, code):
            raise ForbiddenError()
        return user

    return guard
