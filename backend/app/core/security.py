"""Security primitives: Argon2id password hashing, JWT access tokens, opaque refresh tokens."""

import asyncio
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import cache

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import Settings
from app.core.errors import UnauthorizedError

JWT_ALGORITHM = "HS256"  # pinned: tokens claiming any other algorithm are rejected
JWT_ISSUER = "nebula"
JWT_AUDIENCE = "nebula-api"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105  (a claim value, not a secret)

_hasher = PasswordHash((Argon2Hasher(),))


# ─── Passwords ────────────────────────────────────────────


async def hash_password(password: str) -> str:
    # Argon2 is deliberately slow; run it in a thread so the event loop keeps serving.
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    try:
        return await asyncio.to_thread(_hasher.verify, password, password_hash)
    except UnknownHashError:  # e.g. the unusable "!" hash of seeded accounts
        return False


@cache
def _dummy_hash() -> str:
    return _hasher.hash(secrets.token_urlsafe(16))


async def burn_password_check(password: str) -> None:
    """Spend the same time as a real check, so response timing can't reveal unknown emails."""
    await verify_password(password, _dummy_hash())


# ─── Access tokens (JWT) ──────────────────────────────────


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Return the user id, or raise 401 for any expired, tampered or malformed token."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["sub", "exp", "iat", "type"]},
        )
        if claims["type"] != ACCESS_TOKEN_TYPE:
            raise jwt.InvalidTokenError("wrong token type")
        return uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise UnauthorizedError("The access token is invalid or has expired.") from exc


# ─── Refresh tokens (opaque, stored hashed) ───────────────


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # A fast hash is fine here: the token is 256 random bits, so it can't be brute-forced.
    return hashlib.sha256(token.encode()).hexdigest()
