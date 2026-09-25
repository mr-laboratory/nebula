"""Health endpoint and API docs availability."""

from httpx import AsyncClient


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_openapi_docs_available_outside_production(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
