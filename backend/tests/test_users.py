"""The /users/me profile endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import bearer, login, register

ME = "/api/v1/users/me"


async def test_me_returns_own_profile(client: AsyncClient) -> None:
    created = await register(client)
    token = await login(client)

    response = await client.get(ME, headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == created
    assert "password_hash" not in response.json()


async def test_update_profile(client: AsyncClient) -> None:
    await register(client)
    token = await login(client)

    response = await client.patch(
        ME, headers=bearer(token), json={"display_name": "Ada L.", "bio": "Hello"}
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Ada L."
    assert response.json()["bio"] == "Hello"


@pytest.mark.parametrize(
    "payload",
    [{}, {"display_name": None}, {"email": "evil@example.com"}, {"display_name": ""}],
    ids=["empty", "null-name", "email-not-editable", "blank-name"],
)
async def test_invalid_profile_updates_are_rejected(
    client: AsyncClient, payload: dict[str, object]
) -> None:
    await register(client)
    token = await login(client)

    response = await client.patch(ME, headers=bearer(token), json=payload)

    assert response.status_code == 422
    assert (await client.get(ME, headers=bearer(token))).json()["email"] == "ada@example.com"
