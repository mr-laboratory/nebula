"""Application factory. Run with: uvicorn app.main:create_app --factory"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    CompressionMiddleware,
    HTTPCacheMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.session import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # Close pooled connections cleanly on shutdown.
    await app.state.db.dispose()
    await app.state.redis.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    docs_enabled = not settings.is_production
    app = FastAPI(
        title=settings.app_name,
        version="0.7.0",
        debug=settings.app_debug,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    # Both clients connect lazily, so creating the app never needs a running database.
    app.state.db = Database(settings.database_url)
    app.state.redis = Redis.from_url(
        settings.redis_url, socket_timeout=2, socket_connect_timeout=2, decode_responses=True
    )

    # Starlette runs the last-added middleware first, so the order below is inner → outer.
    prefix = settings.api_prefix
    app.add_middleware(
        HTTPCacheMiddleware,
        paths=(f"{prefix}/posts", f"{prefix}/tags", f"{prefix}/users"),  # public reads
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(CompressionMiddleware, skip_paths=(f"{prefix}/auth",))
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app
