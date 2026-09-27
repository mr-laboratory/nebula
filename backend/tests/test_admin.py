"""Roles and account management: the permission matrix, lockout rules, deactivation, audit log."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.schemas.admin import AuditLogFilters
from app.services import admin
from tests.conftest import bearer, create_post, grant_role, login, signed_in

ADMIN = "/api/v1/admin"
POSTS = "/api/v1/posts"


async def audit_entries(client: AsyncClient, auth: dict[str, str], **query: str) -> list[Any]:
    response = await client.get(f"{ADMIN}/audit-logs", params=query, headers=auth)
    assert response.status_code == 200, response.text
    items: list[Any] = response.json()["items"]
    return items


# ─── Permission matrix ────────────────────────────────────

Request = Callable[[AsyncClient, dict[str, str], dict[str, Any]], Any]

# Each protected action, called by the viewer on content owned by "ada".
ACTIONS: dict[str, Request] = {
    "list users": lambda c, h, _: c.get(f"{ADMIN}/users", headers=h),
    "grant role": lambda c, h, _: c.put(f"{ADMIN}/users/ada/roles/moderator", headers=h),
    "revoke role": lambda c, h, _: c.delete(f"{ADMIN}/users/ada/roles/moderator", headers=h),
    "deactivate": lambda c, h, _: c.post(f"{ADMIN}/users/ada/deactivate", headers=h),
    "activate": lambda c, h, _: c.post(f"{ADMIN}/users/ada/activate", headers=h),
    "read audit log": lambda c, h, _: c.get(f"{ADMIN}/audit-logs", headers=h),
    "delete any post": lambda c, h, p: c.delete(f"{POSTS}/{p['id']}", headers=h),
}

# Least privilege: moderators remove content but can't manage people; admins the reverse.
EXPECTED = {
    #                   anonymous user moderator admin
    "list users": (401, 403, 403, 200),
    "grant role": (401, 403, 403, 200),
    "revoke role": (401, 403, 403, 200),
    "deactivate": (401, 403, 403, 200),
    "activate": (401, 403, 403, 200),
    "read audit log": (401, 403, 403, 200),
    "delete any post": (401, 403, 204, 403),
}
VIEWERS = ("anonymous", "user", "moderator", "admin")


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("viewer", VIEWERS)
async def test_permission_matrix(
    client: AsyncClient, app: FastAPI, viewer: str, action: str
) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)
    headers: dict[str, str] = {}
    if viewer != "anonymous":
        headers = await signed_in(client, "viewer")
        if viewer != "user":
            await grant_role(app, "viewer", viewer)

    response: Response = await ACTIONS[action](client, headers, post)

    assert response.status_code == EXPECTED[action][VIEWERS.index(viewer)], response.text


async def test_admin_sees_their_permissions(client: AsyncClient, app: FastAPI) -> None:
    root = await signed_in(client, "root")
    await grant_role(app, "root", "admin")

    me = (await client.get("/api/v1/users/me", headers=root)).json()

    assert me["roles"] == ["admin", "user"]
    assert me["permissions"] == ["audit:read", "user:manage"]  # no moderation rights


# ─── Listing accounts ─────────────────────────────────────


async def test_list_users_filters_and_hides_secrets(client: AsyncClient, app: FastAPI) -> None:
    root = await signed_in(client, "root")
    await grant_role(app, "root", "admin")
    for name in ("ada", "bob"):
        await signed_in(client, name)
    await grant_role(app, "bob", "moderator")

    everyone = (await client.get(f"{ADMIN}/users", headers=root)).json()
    assert everyone["total"] == 3
    assert set(everyone["items"][0]) == {
        "id", "username", "email", "display_name", "is_active", "roles", "created_at"
    }  # fmt: skip

    async def names(**query: str) -> list[str]:
        response = await client.get(f"{ADMIN}/users", params=query, headers=root)
        return [user["username"] for user in response.json()["items"]]

    assert await names(q="BOB@") == ["bob"]  # email match, case-insensitive
    assert await names(role="moderator") == ["bob"]
    assert await names(q="%") == []  # wildcards are searched literally


# ─── Roles ────────────────────────────────────────────────


async def test_grant_and_revoke_are_idempotent_and_audited(
    client: AsyncClient, app: FastAPI
) -> None:
    root = await signed_in(client, "root")
    await grant_role(app, "root", "admin")
    await signed_in(client, "ada")
    url = f"{ADMIN}/users/ada/roles/moderator"

    for _ in range(2):
        granted = await client.put(url, headers=root)
        assert granted.status_code == 200
        assert granted.json()["roles"] == ["moderator", "user"]
    for _ in range(2):
        revoked = await client.delete(url, headers=root)
        assert revoked.json()["roles"] == ["user"]

    entries = await audit_entries(client, root)
    assert [(e["action"], e["actor"], e["details"]) for e in entries] == [
        ("role.revoke", "root", {"role": "moderator"}),
        ("role.grant", "root", {"role": "moderator"}),
    ]  # newest first, and each change logged once
    assert entries[0]["target_id"] == granted.json()["id"]


async def test_role_errors(client: AsyncClient, app: FastAPI) -> None:
    root = await signed_in(client, "root")
    await grant_role(app, "root", "admin")
    await signed_in(client, "ada")

    assert (await client.put(f"{ADMIN}/users/ada/roles/wizard", headers=root)).status_code == 404
    assert (await client.put(f"{ADMIN}/users/nobody/roles/admin", headers=root)).status_code == 404
    assert (await client.delete(f"{ADMIN}/users/ada/roles/user", headers=root)).status_code == 409
    assert (await client.put(f"{ADMIN}/users/ada/roles/Bad!", headers=root)).status_code == 422


async def test_admins_cannot_lock_themselves_out(client: AsyncClient, app: FastAPI) -> None:
    root = await signed_in(client, "root")
    ada = await signed_in(client, "ada")
    await grant_role(app, "root", "admin")
    await grant_role(app, "ada", "admin")

    assert (await client.delete(f"{ADMIN}/users/root/roles/admin", headers=root)).status_code == 409
    assert (await client.post(f"{ADMIN}/users/root/deactivate", headers=root)).status_code == 409
    # Another admin can, though, and the demoted admin loses access at once.
    assert (await client.delete(f"{ADMIN}/users/root/roles/admin", headers=ada)).status_code == 200
    assert (await client.get(f"{ADMIN}/users", headers=root)).status_code == 403


async def test_the_last_admin_cannot_be_removed_even_from_the_cli(app: FastAPI) -> None:
    async with app.state.db.sessionmaker() as session:
        await session.execute(
            text(
                "INSERT INTO users (email, username, password_hash, display_name) "
                "VALUES ('root@example.com', 'root', '!', 'Root')"
            )
        )
        await admin.grant_role(session, None, "root", "admin")  # how the first admin is made
        with pytest.raises(ConflictError):
            await admin.revoke_role(session, None, "root", "admin")
        with pytest.raises(ConflictError):
            await admin.set_active(session, None, "root", active=False)
        await session.commit()

        entries = await admin.list_audit_logs(session, AuditLogFilters())
    assert [(e.action, e.actor) for e in entries.items] == [("role.grant", None)]


# ─── Deactivation ─────────────────────────────────────────


async def test_deactivation_signs_out_and_hides_the_account(
    client: AsyncClient, app: FastAPI
) -> None:
    root = await signed_in(client, "root")
    await grant_role(app, "root", "admin")
    ada = await signed_in(client, "ada")  # last login: the client now holds ada's refresh cookie

    response = await client.post(f"{ADMIN}/users/ada/deactivate", headers=root)
    assert response.json()["is_active"] is False

    assert (await client.get("/api/v1/users/me", headers=ada)).status_code == 401  # access token
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401  # refresh token
    denied = await client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "correct-horse-battery"}
    )
    assert denied.status_code == 401
    assert (await client.get("/api/v1/users/ada")).status_code == 404

    await client.post(f"{ADMIN}/users/ada/activate", headers=root)
    assert (
        await client.get("/api/v1/users/me", headers=bearer(await login(client, "ada")))
    ).is_success
    actions = [e["action"] for e in await audit_entries(client, root)]
    assert actions == ["user.activate", "user.deactivate"]


# ─── Moderation is audited ────────────────────────────────


async def test_moderator_deletes_are_audited_but_own_deletes_are_not(
    client: AsyncClient, app: FastAPI
) -> None:
    root = await signed_in(client, "root")
    ada = await signed_in(client, "ada")
    mod = await signed_in(client, "mod")
    await grant_role(app, "root", "admin")
    await grant_role(app, "mod", "moderator")
    removed = await create_post(client, ada, publish=True, title="Spam")
    own = await create_post(client, ada, publish=True, title="Mine")
    comment = (
        await client.post(f"{POSTS}/{own['id']}/comments", json={"body": "Hi"}, headers=root)
    ).json()

    assert (await client.delete(f"{POSTS}/{removed['id']}", headers=mod)).status_code == 204
    assert (
        await client.delete(f"/api/v1/comments/{comment['id']}", headers=mod)
    ).status_code == 204
    assert (await client.delete(f"{POSTS}/{own['id']}", headers=ada)).status_code == 204

    entries = await audit_entries(client, root, actor="mod")
    assert [(e["action"], e["target_type"], e["target_id"]) for e in entries] == [
        ("comment.delete", "comment", comment["id"]),
        ("post.delete", "post", removed["id"]),
    ]
    assert entries[0]["details"] == {"post_id": own["id"]}
    assert await audit_entries(client, root, actor="ada") == []
    assert [e["action"] for e in await audit_entries(client, root, action="post.delete")] == [
        "post.delete"
    ]


async def test_audit_log_is_append_only(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "INSERT INTO audit_logs (action, target_type, target_id) "
            "VALUES ('user.activate', 'user', gen_random_uuid())"
        )
    )
    for statement in ("UPDATE audit_logs SET action = 'x'", "DELETE FROM audit_logs"):
        with pytest.raises(DBAPIError, match="append-only"):
            async with db_session.begin_nested():
                await db_session.execute(text(statement))
