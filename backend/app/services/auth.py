"""Registration, login and refresh-token rotation with reuse detection."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    burn_password_check,
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.models import RefreshToken, Role, User
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)

DEFAULT_ROLE = "user"  # least privilege: new accounts get only the basic role
ACCOUNT_TAKEN = "An account with this email or username already exists."
INVALID_CREDENTIALS = "Invalid email or password."
SESSION_EXPIRED = "Your session has expired. Please sign in again."


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    refresh_record: RefreshToken


async def register(session: AsyncSession, data: RegisterRequest) -> User:
    taken = await session.scalar(
        select(User.id).where(or_(User.email == data.email, User.username == data.username))
    )
    if taken is not None:
        raise ConflictError(ACCOUNT_TAKEN)

    role = (await session.execute(select(Role).where(Role.name == DEFAULT_ROLE))).scalar_one()
    user = User(
        email=data.email,
        username=data.username,
        password_hash=await hash_password(data.password.get_secret_value()),
        display_name=data.display_name,
        roles=[role],
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:  # lost a race with a concurrent registration
        raise ConflictError(ACCOUNT_TAKEN) from exc

    logger.info("user registered", extra={"user_id": str(user.id)})
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    """Return the user, or raise one generic 401 whatever the reason (no account enumeration)."""
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        await burn_password_check(password)
        reason = "unknown_email"
    elif not await verify_password(password, user.password_hash):
        reason = "wrong_password"
    elif not user.is_active:
        reason = "inactive"
    else:
        return user
    logger.info("login failed", extra={"reason": reason})
    raise UnauthorizedError(INVALID_CREDENTIALS)


async def issue_tokens(
    session: AsyncSession,
    user_id: uuid.UUID,
    settings: Settings,
    family_id: uuid.UUID | None = None,
) -> IssuedTokens:
    raw = new_refresh_token()
    record = RefreshToken(
        user_id=user_id,
        family_id=family_id or uuid.uuid4(),
        token_hash=hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    session.add(record)
    await session.flush()
    return IssuedTokens(create_access_token(user_id, settings), raw, record)


async def rotate(session: AsyncSession, raw_token: str, settings: Settings) -> IssuedTokens:
    """Swap a valid refresh token for a new pair. Reusing an old token revokes its family."""
    record = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw_token))
        .with_for_update()  # serialise concurrent refreshes of the same token
    )
    if record is None:
        raise UnauthorizedError(SESSION_EXPIRED)

    if record.revoked_at is not None:
        # An already-used token came back: someone else has a copy. End the whole session.
        await _revoke_family(session, record.family_id)
        await session.commit()  # keep the revocation even though this request fails
        logger.warning(
            "refresh token reuse detected",
            extra={"user_id": str(record.user_id), "family_id": str(record.family_id)},
        )
        raise UnauthorizedError(SESSION_EXPIRED)

    user = await session.get(User, record.user_id)
    if record.expires_at <= datetime.now(UTC) or user is None or not user.is_active:
        raise UnauthorizedError(SESSION_EXPIRED)

    record.revoked_at = datetime.now(UTC)
    issued = await issue_tokens(session, user.id, settings, family_id=record.family_id)
    record.replaced_by_id = issued.refresh_record.id
    return issued


async def logout(session: AsyncSession, raw_token: str) -> None:
    record = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))
    )
    if record is not None:
        await _revoke_family(session, record.family_id)


async def _revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=func.now())
    )
