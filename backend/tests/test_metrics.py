"""Prometheus metrics (bounded labels, no user data) and per-request log correlation."""

import json
import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.main import create_app
from tests.conftest import create_post, signed_in

METRICS = "/metrics"


def series(text: str, name: str, **labels: str) -> float:
    """Value of the metric line whose labels include `labels` (0 if absent)."""
    for line in text.splitlines():
        if line.startswith(name + "{") and all(f'{k}="{v}"' in line for k, v in labels.items()):
            return float(line.rsplit(" ", 1)[1])
    return 0.0


async def scrape(client: AsyncClient) -> str:
    response = await client.get(METRICS)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    return response.text


async def test_requests_are_counted_by_route_template(client: AsyncClient) -> None:
    auth = await signed_in(client)
    post = await create_post(client, auth, publish=True)
    labels = {"method": "GET", "route": "/api/v1/posts/{slug}", "status": "200"}
    before = series(await scrape(client), "nebula_http_requests_total", **labels)

    await client.get(f"/api/v1/posts/{post['slug']}")
    text = await scrape(client)

    assert series(text, "nebula_http_requests_total", **labels) == before + 1
    assert post["slug"] not in text  # the template, never the real value
    assert series(text, "nebula_http_request_duration_seconds_count", route="/api/v1/posts/{slug}")


async def test_unknown_paths_and_methods_share_one_series(client: AsyncClient) -> None:
    await client.get("/no-such-page-8f3a")
    await client.request("BREW", "/api/v1/posts")
    text = await scrape(client)

    assert "no-such-page-8f3a" not in text
    assert "BREW" not in text
    assert series(text, "nebula_http_requests_total", route="unmatched", status="404")
    assert series(text, "nebula_http_requests_total", method="OTHER")


async def test_scrapes_are_not_counted(client: AsyncClient) -> None:
    await scrape(client)

    assert 'route="/metrics"' not in await scrape(client)


async def test_metrics_are_not_part_of_the_public_api_docs(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()

    assert METRICS not in schema["paths"]


async def test_metrics_can_be_turned_off(migrated_db: None, settings: Settings) -> None:
    app: FastAPI = create_app(settings.model_copy(update={"metrics_enabled": False}))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as ac:
        assert (await ac.get(METRICS)).status_code == 404
    await app.state.db.dispose()
    await app.state.redis.aclose()


def access_logs(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    formatter = JsonFormatter()
    return [json.loads(formatter.format(r)) for r in caplog.records if r.name == "nebula.access"]


async def test_access_log_carries_route_and_user_id(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    auth = await signed_in(client)
    me = (await client.get("/api/v1/users/me", headers=auth)).json()
    caplog.clear()
    caplog.set_level(logging.INFO, logger="nebula.access")

    await client.get("/api/v1/users/me", headers=auth)
    await client.get("/api/v1/health/live")

    signed_in_line, anonymous_line = access_logs(caplog)
    assert signed_in_line["route"] == "/api/v1/users/me"
    assert signed_in_line["user_id"] == me["id"]
    assert "user_id" not in anonymous_line  # not leaked from the previous request


async def test_unhandled_errors_are_logged_with_context_but_no_input(
    app: FastAPI, client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    @app.post("/boom/{thing}")
    async def boom(thing: str) -> None:
        raise RuntimeError("kaboom")

    caplog.set_level(logging.ERROR, logger="nebula.access")
    response = await client.post("/boom/x", json={"password": "hunter2"})

    assert response.status_code == 500
    assert "kaboom" not in response.text  # the client sees a generic problem
    (record,) = [r for r in caplog.records if r.levelno == logging.ERROR]
    line = JsonFormatter().format(record)
    assert json.loads(line)["route"] == "/boom/{thing}"
    assert "kaboom" in line  # the traceback is in the log...
    assert "hunter2" not in line  # ...the request body is not
