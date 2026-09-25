"""Readiness checks for Postgres and Redis. Failures are logged, never returned to clients."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Literal

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

CheckResult = Literal["ok", "fail"]

logger = logging.getLogger(__name__)

CHECK_TIMEOUT_SECONDS = 2.0


async def _run(name: str, check: Callable[[], Awaitable[object]]) -> CheckResult:
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            await check()
    except Exception as exc:
        # Log only the exception type: messages can contain hostnames or credentials.
        logger.warning("readiness check failed", extra={"check": name, "error": type(exc).__name__})
        return "fail"
    return "ok"


async def check_database(engine: AsyncEngine) -> CheckResult:
    async def ping() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    return await _run("database", ping)


async def check_redis(redis: Redis) -> CheckResult:
    async def ping() -> None:
        await redis.ping()

    return await _run("redis", ping)


async def readiness(engine: AsyncEngine, redis: Redis) -> dict[str, CheckResult]:
    database, cache = await asyncio.gather(check_database(engine), check_redis(redis))
    return {"database": database, "redis": cache}
