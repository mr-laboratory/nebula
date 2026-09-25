"""Fixed-window rate limiting on Redis (INCR + EXPIRE), used to slow down password guessing."""

import hashlib
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.errors import RateLimitedError

logger = logging.getLogger(__name__)

KEY_PREFIX = "rl"


def key_part(value: str) -> str:
    """Hash identifiers such as emails so no personal data is stored in Redis keys."""
    return hashlib.sha256(value.lower().encode()).hexdigest()[:32]


async def enforce(redis: Redis, scope: str, identity: str, *, limit: int, window: int) -> None:
    """Raise 429 once `identity` exceeds `limit` hits in the current `window` seconds."""
    key = f"{KEY_PREFIX}:{scope}:{key_part(identity)}"
    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window, nx=True)  # start the window on the first hit only
            pipe.ttl(key)
            hits, _, ttl = await pipe.execute()
    except RedisError as exc:
        # Fail open: an unavailable limiter must not lock everyone out. Readiness reports it.
        logger.warning("rate limiter unavailable", extra={"error": type(exc).__name__})
        return
    if int(hits) > limit:
        raise RateLimitedError(retry_after=max(int(ttl), 1))
