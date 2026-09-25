"""Shared pytest fixtures: test settings, a migrated test database, app and HTTP client.

Tests use the separate `<POSTGRES_DB>_test` database. The schema is migrated once per run,
and every DB test runs inside a transaction that is rolled back, so tests never leak data.
"""

from collections.abc import AsyncIterator, Iterator
from functools import cache
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.main import create_app

TEST_SECRET = "test-secret-" + "x" * 40
BACKEND_DIR = Path(__file__).resolve().parents[1]


@cache
def build_test_settings() -> Settings:
    # Connection details come from the environment / .env (like the real app); everything
    # security- or behaviour-related is pinned so a developer's .env cannot change tests.
    local = Settings(jwt_secret=TEST_SECRET)
    return Settings(
        _env_file=None,
        app_env="test",
        jwt_secret=TEST_SECRET,
        postgres_user=local.postgres_user,
        postgres_password=local.postgres_password,
        postgres_host=local.postgres_host,
        postgres_port=local.postgres_port,
        postgres_db=f"{local.postgres_db}_test",
        redis_url=local.redis_url,
    )


def alembic_config(settings: Settings) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = settings.database_url
    return config


@pytest.fixture(scope="session")
def migrated_db() -> Iterator[None]:
    config = alembic_config(build_test_settings())
    command.downgrade(config, "base")  # start clean even if a previous run crashed
    command.upgrade(config, "head")
    yield


@pytest.fixture
def settings() -> Settings:
    return build_test_settings()


@pytest.fixture
async def db_session(migrated_db: None, settings: Settings) -> AsyncIterator[AsyncSession]:
    """A session whose work (including commits) is rolled back after the test."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
    await engine.dispose()


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    yield application
    # httpx's ASGITransport does not run the lifespan, so close clients here.
    await application.state.db.dispose()
    await application.state.redis.aclose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
