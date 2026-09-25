"""Health endpoints used by Docker and monitoring: liveness (process) and readiness (deps)."""

from typing import Literal, cast

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from app.api.deps import RedisDep
from app.db.session import Database
from app.services.health import CheckResult, readiness

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok"]


class ReadinessStatus(BaseModel):
    status: Literal["ok", "unavailable"]
    checks: dict[str, CheckResult]


@router.get("/live", summary="Liveness probe")
async def live() -> HealthStatus:
    """The process is up and able to serve requests."""
    return HealthStatus(status="ok")


@router.get(
    "/ready",
    summary="Readiness probe",
    responses={503: {"model": ReadinessStatus, "description": "A dependency is unavailable"}},
)
async def ready(request: Request, response: Response, redis: RedisDep) -> ReadinessStatus:
    """Postgres and Redis are reachable. Returns 503 if either check fails."""
    db = cast(Database, request.app.state.db)
    checks = await readiness(db.engine, redis)
    if all(result == "ok" for result in checks.values()):
        return ReadinessStatus(status="ok", checks=checks)
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessStatus(status="unavailable", checks=checks)
