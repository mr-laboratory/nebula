"""Shared pytest fixtures: isolated settings, app instance and async HTTP client."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

TEST_SECRET = "test-secret-" + "x" * 40


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: tests never read a developer's local .env
    return Settings(_env_file=None, app_env="test", jwt_secret=TEST_SECRET)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
