"""Shared pytest fixtures: test settings, a migrated test database, app and HTTP client.

Tests use the separate `<POSTGRES_DB>_test` database and Redis database 15. The schema is
migrated once per run. `db_session` tests run in a rolled-back transaction; API tests
(`client`) commit for real, so user data is truncated and Redis flushed around each one.
"""

from collections.abc import AsyncIterator, Iterator
from functools import cache
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.main import create_app

TEST_SECRET = "test-secret-" + "x" * 40
TEST_PASSWORD = "correct-horse-battery"
TEST_REDIS_DB = 15
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
        redis_url=f"{local.redis_url.rsplit('/', 1)[0]}/{TEST_REDIS_DB}",
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
async def app(migrated_db: None, settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    await application.state.redis.flushdb()  # fresh rate-limit counters
    yield application
    async with application.state.db.engine.begin() as conn:
        # Roles and permissions are reference data from migrations, so they stay.
        await conn.execute(text("TRUNCATE users, tags RESTART IDENTITY CASCADE"))
    # httpx's ASGITransport does not run the lifespan, so close clients here.
    await application.state.db.dispose()
    await application.state.redis.aclose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    # https: the refresh cookie is Secure, so the client only sends it over HTTPS.
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac


async def register(client: AsyncClient, name: str = "ada", **overrides: str) -> dict[str, object]:
    payload = {
        "email": f"{name}@example.com",
        "username": name,
        "password": TEST_PASSWORD,
        "display_name": name.title(),
        **overrides,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


async def login(client: AsyncClient, name: str = "ada", password: str = TEST_PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": f"{name}@example.com", "password": password}
    )
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
