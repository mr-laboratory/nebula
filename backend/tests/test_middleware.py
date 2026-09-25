"""Request-id handling, security headers and CORS policy."""

from httpx import AsyncClient

HEALTH = "/api/v1/health/live"


async def test_request_id_generated_when_missing(client: AsyncClient) -> None:
    response = await client.get(HEALTH)

    assert len(response.headers["X-Request-ID"]) == 32


async def test_valid_request_id_is_propagated(client: AsyncClient) -> None:
    response = await client.get(HEALTH, headers={"X-Request-ID": "trace-1234abcd"})

    assert response.headers["X-Request-ID"] == "trace-1234abcd"


async def test_unsafe_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get(HEALTH, headers={"X-Request-ID": "bad id\nforged-log-line"})

    assert response.headers["X-Request-ID"] != "bad id\nforged-log-line"
    assert len(response.headers["X-Request-ID"]) == 32


async def test_security_headers_present(client: AsyncClient) -> None:
    response = await client.get(HEALTH)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert (
        response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    )
    assert "Strict-Transport-Security" not in response.headers  # HTTPS-only, production


async def test_cors_allows_only_configured_origin(client: AsyncClient) -> None:
    preflight = {"Access-Control-Request-Method": "GET"}
    allowed = await client.options(HEALTH, headers={"Origin": "http://localhost:5173", **preflight})
    blocked = await client.options(HEALTH, headers={"Origin": "https://evil.example", **preflight})

    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Access-Control-Allow-Origin" not in blocked.headers
