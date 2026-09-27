"""Prometheus metrics: request counts and latency per route, served at GET /metrics.

Labels only ever take a small, fixed set of values (route templates, known methods, status
codes), never ids, slugs or usernames. Each distinct label combination is a separate time
series, so an unbounded label would let any client grow the server's memory at will.
"""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Scope

METRICS_PATH = "/metrics"
UNMATCHED = "unmatched"
_KNOWN_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})

REQUESTS = Counter(
    "nebula_http_requests",
    "HTTP requests handled, by route template and status code",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "nebula_http_request_duration_seconds",
    "Time to handle an HTTP request, by route template",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


def route_label(scope: Scope) -> str:
    """The matched route's template (`/api/v1/posts/{slug}`), or `unmatched` for 404s."""
    # FastAPI keeps included routers nested, so `scope["route"]` knows only its own router's
    # prefix; the full template is on FastAPI's route context. Either way it's a template.
    context = scope.get("fastapi", {}).get("effective_route_context")
    route = scope.get("route")
    return getattr(context, "path", None) or getattr(route, "path_format", None) or UNMATCHED


def observe(scope: Scope, status: int, seconds: float) -> None:
    if scope["path"] == METRICS_PATH:
        return  # scrapes would otherwise dominate the numbers
    method = scope["method"] if scope["method"] in _KNOWN_METHODS else "OTHER"
    route = route_label(scope)
    REQUESTS.labels(method, route, str(status)).inc()
    LATENCY.labels(method, route).observe(seconds)


async def metrics_endpoint(_: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
