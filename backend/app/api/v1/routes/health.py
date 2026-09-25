"""Health endpoints used by Docker and monitoring to check the service."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok"]


@router.get("/live", summary="Liveness probe")
async def live() -> HealthStatus:
    """The process is up and able to serve requests."""
    return HealthStatus(status="ok")
