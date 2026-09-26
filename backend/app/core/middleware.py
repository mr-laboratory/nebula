"""ASGI middleware: request context, security headers, HTTP caching (ETag) and compression."""

import hashlib
import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import problem_response
from app.core.logging import request_id_ctx

logger = logging.getLogger("nebula.access")

REQUEST_ID_HEADER = "X-Request-ID"
# Accept client-supplied ids only if they are short and plain (prevents log injection).
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")

DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")
API_CSP = "default-src 'none'; frame-ancestors 'none'"


class RequestContextMiddleware:
    """Assigns a request id, logs one line per request, and turns crashes into safe 500s."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(REQUEST_ID_HEADER.lower().encode(), b"").decode()
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("unhandled error")
            if not response_started:
                response = problem_response(
                    500,
                    "An unexpected error occurred.",
                    scope["path"],
                    headers={REQUEST_ID_HEADER: request_id},
                )
                await response(scope, receive, send)
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware:
    """Adds defensive browser headers to every HTTP response."""

    def __init__(self, app: ASGIApp, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_docs = scope["path"].startswith(DOCS_PATHS)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Cross-Origin-Opener-Policy"] = "same-origin"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                if not is_docs:  # Swagger UI needs its CDN scripts; the JSON API needs nothing.
                    headers["Content-Security-Policy"] = API_CSP
                    headers["Cache-Control"] = headers.get("Cache-Control", "no-store")
                if self.hsts:
                    headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
            await send(message)

        await self.app(scope, receive, send_wrapper)


def _etag_matches(if_none_match: str, etag: str) -> bool:
    # Weak comparison (RFC 9110): W/"x" and "x" name the same representation.
    if if_none_match.strip() == "*":
        return True
    return etag.removeprefix("W/") in {
        tag.strip().removeprefix("W/") for tag in if_none_match.split(",")
    }


class HTTPCacheMiddleware:
    """ETags for anonymous public GETs, so an unchanged page is answered with an empty 304.

    Responses are revalidated on every use (`no-cache`), so like counts are never stale.
    Requests with an Authorization header are left alone: they can carry per-viewer data
    (drafts, liked_by_me) and keep the default `no-store`.
    """

    def __init__(self, app: ASGIApp, *, paths: tuple[str, ...]) -> None:
        self.app = app
        self.paths = paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request_headers = Headers(scope=scope) if scope["type"] == "http" else Headers()
        if (
            scope["type"] != "http"
            or scope["method"] != "GET"
            or not scope["path"].startswith(self.paths)
            or "authorization" in request_headers
        ):
            await self.app(scope, receive, send)
            return

        start: Message = {}
        chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
                if start["status"] != 200:
                    await send(message)
                return
            if start["status"] != 200:
                await send(message)
                return
            # Buffer the (small, JSON) body: the ETag is a hash of all of it.
            chunks.append(message.get("body", b""))
            if message.get("more_body"):
                return
            body = b"".join(chunks)
            headers = MutableHeaders(scope=start)
            headers["ETag"] = etag = f'W/"{hashlib.sha256(body).hexdigest()[:32]}"'
            headers["Cache-Control"] = "no-cache"
            headers.add_vary_header("Authorization")
            if _etag_matches(request_headers.get("if-none-match", ""), etag):
                await send({**start, "status": 304, "headers": _without_body_headers(start)})
                await send({"type": "http.response.body", "body": b""})
                return
            await send(start)
            await send({"type": "http.response.body", "body": body})

        await self.app(scope, receive, send_wrapper)


def _without_body_headers(start: Message) -> list[tuple[bytes, bytes]]:
    dropped = {b"content-length", b"content-type"}
    return [(key, value) for key, value in start["headers"] if key.lower() not in dropped]


class CompressionMiddleware:
    """Gzip for large responses, except auth endpoints.

    Compressing a secret (a token) next to attacker-influenced input can leak it through
    the compressed size (BREACH), so responses carrying tokens are never compressed.
    """

    def __init__(self, app: ASGIApp, *, skip_paths: tuple[str, ...], minimum_size: int = 1000):
        self.app = app
        self.skip_paths = skip_paths
        self.gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith(self.skip_paths):
            await self.app(scope, receive, send)
            return
        await self.gzip(scope, receive, send)
