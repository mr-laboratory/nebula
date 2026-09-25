"""Auth flows: registration, login, token validation, refresh rotation, logout, rate limits."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text

from app.core.security import JWT_AUDIENCE, JWT_ISSUER
from tests.conftest import TEST_PASSWORD, TEST_SECRET, bearer, login, register

REFRESH_COOKIE = "nebula_refresh"
ME = "/api/v1/users/me"


def refresh_cookie(value: str) -> dict[str, str]:
    return {"Cookie": f"{REFRESH_COOKIE}={value}"}


# ─── Registration ─────────────────────────────────────────


async def test_register_creates_user_with_basic_role(client: AsyncClient) -> None:
    body = await register(client, "ada", email="Ada@Example.com")

    assert body["email"] == "ada@example.com"  # normalised
    assert body["roles"] == ["user"]
    assert body["permissions"] == []
    assert "password" not in str(body)
    assert "password_hash" not in body


@pytest.mark.parametrize(
    "overrides",
    [{"email": "ADA@example.com", "username": "other"}, {"username": "ADA"}],
    ids=["email", "username"],
)
async def test_register_rejects_taken_email_or_username(
    client: AsyncClient, overrides: dict[str, str]
) -> None:
    await register(client, "ada")
    payload = {
        "email": "new@example.com",
        "password": TEST_PASSWORD,
        "display_name": "X",
        **overrides,
    }

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409


async def test_register_rejects_short_password_without_echoing_it(client: AsyncClient) -> None:
    payload = {
        "email": "a@example.com",
        "username": "ada",
        "password": "short-pw",
        "display_name": "Ada",
    }

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert "short-pw" not in response.text


# ─── Login ────────────────────────────────────────────────


async def test_login_returns_token_and_secure_refresh_cookie(client: AsyncClient) -> None:
    await register(client)

    response = await client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 15 * 60
    cookie = response.headers["set-cookie"].lower()
    for attribute in ("httponly", "secure", "samesite=strict", "path=/api/v1/auth"):
        assert attribute in cookie


async def test_login_failures_are_indistinguishable(client: AsyncClient) -> None:
    await register(client)

    wrong_password = await client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "wrong-password-1"}
    )
    unknown_email = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]
    assert wrong_password.headers["www-authenticate"] == "Bearer"


async def test_deactivated_user_is_locked_out(client: AsyncClient, app: FastAPI) -> None:
    await register(client)
    token = await login(client)
    async with app.state.db.engine.begin() as conn:
        await conn.execute(text("UPDATE users SET is_active = false"))

    assert (await client.get(ME, headers=bearer(token))).status_code == 401
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401


async def test_login_is_rate_limited_per_ip(client: AsyncClient) -> None:
    attempt = {"email": "ada@example.com", "password": "wrong-password-1"}
    statuses = [
        (await client.post("/api/v1/auth/login", json=attempt)).status_code for _ in range(6)
    ]

    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
    response = await client.post("/api/v1/auth/login", json=attempt)
    assert int(response.headers["retry-after"]) > 0


async def test_logs_never_contain_passwords_or_emails(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await register(client)
    await client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "wrong-password-1"}
    )
    await login(client)

    logged = " ".join(str(record.__dict__) for record in caplog.records)
    assert "user registered" in logged and "login failed" in logged
    for private in (TEST_PASSWORD, "wrong-password-1", "ada@example.com"):
        assert private not in logged


# ─── Access tokens ────────────────────────────────────────


def forge(secret: str = TEST_SECRET, algorithm: str = "HS256", **claims: object) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **claims,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


async def test_me_requires_a_token(client: AsyncClient) -> None:
    response = await client.get(ME)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "make_token",
    [
        lambda sub: forge(sub=sub, exp=datetime.now(UTC) - timedelta(seconds=1)),
        lambda sub: forge(sub=sub, secret="another-secret-" + "y" * 40),
        lambda sub: forge(sub=sub, type="refresh"),
        lambda sub: forge(sub=sub, aud="someone-else"),
        lambda sub: forge(sub=sub, algorithm="none", secret=""),
        lambda sub: "not-a-jwt",
    ],
    ids=["expired", "wrong-signature", "wrong-type", "wrong-audience", "alg-none", "garbage"],
)
async def test_invalid_access_tokens_are_rejected(client: AsyncClient, make_token: object) -> None:
    user = await register(client)
    token = make_token(user["id"])  # type: ignore[operator]

    response = await client.get(ME, headers=bearer(token))

    assert response.status_code == 401


async def test_tampered_token_is_rejected(client: AsyncClient) -> None:
    await register(client)
    header, payload, signature = (await login(client)).split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}{'AA' if signature[-2:] != 'AA' else 'BB'}"

    assert (await client.get(ME, headers=bearer(tampered))).status_code == 401


# ─── Refresh & logout ─────────────────────────────────────


async def test_refresh_rotates_the_token(client: AsyncClient) -> None:
    await register(client)
    await login(client)
    first = client.cookies[REFRESH_COOKIE]

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert client.cookies[REFRESH_COOKIE] != first
    assert (
        await client.get(ME, headers=bearer(response.json()["access_token"]))
    ).status_code == 200


async def test_reusing_a_rotated_token_revokes_the_whole_session(client: AsyncClient) -> None:
    await register(client)
    await login(client)
    stolen = client.cookies[REFRESH_COOKIE]
    client.cookies.clear()  # from here on, cookies are sent explicitly

    legit = await client.post("/api/v1/auth/refresh", headers=refresh_cookie(stolen))
    assert legit.status_code == 200  # control: explicitly sent cookies do reach the API
    current = legit.cookies[REFRESH_COOKIE]

    replay = await client.post("/api/v1/auth/refresh", headers=refresh_cookie(stolen))
    after = await client.post("/api/v1/auth/refresh", headers=refresh_cookie(current))

    assert replay.status_code == 401
    assert after.status_code == 401  # the legitimate token died with its family


async def test_refresh_without_cookie_is_rejected(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh_token_and_clears_cookie(client: AsyncClient) -> None:
    await register(client)
    await login(client)
    token = client.cookies[REFRESH_COOKIE]

    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert REFRESH_COOKIE not in client.cookies
    reuse = await client.post("/api/v1/auth/refresh", headers=refresh_cookie(token))
    assert reuse.status_code == 401


async def test_logout_is_idempotent(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/auth/logout")).status_code == 204
