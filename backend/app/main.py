"""Application factory. Run with: uvicorn app.main:create_app --factory"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.api.v1.routes import writing
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import METRICS_PATH, metrics_endpoint
from app.core.middleware import (
    BodySizeLimitMiddleware,
    CompressionMiddleware,
    HTTPCacheMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.session import Database

# Largest request body accepted (imports are the biggest: a 1 MB file plus multipart framing).
MAX_BODY_BYTES = 2 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # Close pooled connections cleanly on shutdown.
    await app.state.db.dispose()
    await app.state.redis.aclose()
    await app.state.http.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    docs_enabled = not settings.is_production
    app = FastAPI(
        title=settings.app_name,
        version="0.10.0",
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
    # Outbound calls to third-party APIs (LanguageTool). Shared, so connections are reused.
    app.state.http = httpx.AsyncClient(
        timeout=settings.languagetool_timeout_seconds,
        headers={"User-Agent": f"nebula/{app.version}"},
        follow_redirects=False,
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
    # Exports stream binary files that are already compressed (docx is a zip, pdf has its own).
    app.add_middleware(CompressionMiddleware, skip_paths=(f"{prefix}/auth", f"{prefix}/exports"))
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_BODY_BYTES)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    if settings.writing_check_enabled:  # off: no draft text ever leaves the server
        app.include_router(writing.router, prefix=settings.api_prefix)
    if settings.metrics_enabled:
        app.add_route(METRICS_PATH, metrics_endpoint, include_in_schema=False)
    return app
