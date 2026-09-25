"""Error handling: Problem Details shape and no leakage of internals or input."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import BaseModel

from app.core.errors import ForbiddenError, NotFoundError


class Credentials(BaseModel):
    email: str
    password: str


@pytest.fixture(autouse=True)
def error_routes(app: FastAPI) -> None:
    @app.get("/boom/not-found")
    async def not_found() -> None:
        raise NotFoundError("Post not found")

    @app.get("/boom/forbidden")
    async def forbidden() -> None:
        raise ForbiddenError()

    @app.get("/boom/crash")
    async def crash() -> None:
        raise RuntimeError("db password=hunter2 leaked in stack trace")

    @app.post("/boom/login")
    async def login(body: Credentials) -> None:
        return None


async def test_domain_error_becomes_problem_details(client: AsyncClient) -> None:
    response = await client.get("/boom/not-found")
    body = response.json()

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert body["title"] == "Not Found"
    assert body["detail"] == "Post not found"
    assert body["instance"] == "/boom/not-found"
    assert body["request_id"] == response.headers["X-Request-ID"]


async def test_default_detail_used_when_none_given(client: AsyncClient) -> None:
    response = await client.get("/boom/forbidden")

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to perform this action."


async def test_unknown_route_is_problem_details(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


async def test_unexpected_error_hides_internals(client: AsyncClient) -> None:
    response = await client.get("/boom/crash")

    assert response.status_code == 500
    assert response.json()["detail"] == "An unexpected error occurred."
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


async def test_validation_error_never_echoes_input(client: AsyncClient) -> None:
    response = await client.post("/boom/login", json={"password": "S3cret-Passw0rd!"})
    body = response.json()

    assert response.status_code == 422
    assert body["errors"][0]["loc"] == ["body", "email"]
    assert "S3cret-Passw0rd!" not in response.text
