"""Health endpoints (liveness, readiness) and API docs availability."""

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_openapi_docs_available_outside_production(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200


async def test_readiness_ok_when_dependencies_are_up(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


async def test_readiness_503_without_leaking_details(settings: Settings) -> None:
    broken = settings.model_copy(update={"postgres_port": 1, "redis_url": "redis://127.0.0.1:1/0"})
    app = create_app(broken)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
    finally:
        await app.state.db.dispose()
        await app.state.redis.aclose()

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "fail", "redis": "fail"},
    }
