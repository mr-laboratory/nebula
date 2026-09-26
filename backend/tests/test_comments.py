"""Comments: public reading, who may write, edit and delete, soft-delete placeholders, limits."""

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import create_post, grant_role, signed_in

POSTS = "/api/v1/posts"
COMMENTS = "/api/v1/comments"


async def comment(
    client: AsyncClient, auth: dict[str, str], post: dict[str, Any], body: str = "Nice post!"
) -> dict[str, Any]:
    response = await client.post(
        f"{POSTS}/{post['id']}/comments", json={"body": body}, headers=auth
    )
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def listing(client: AsyncClient, post: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    response = await client.get(f"{POSTS}/{post['id']}/comments", **kwargs)
    assert response.status_code == 200, response.text
    page: dict[str, Any] = response.json()
    return page


# ─── Reading & writing ────────────────────────────────────


async def test_comments_are_public_and_oldest_first(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    post = await create_post(client, ada, publish=True)
    await comment(client, bob, post, "  First!  ")
    await comment(client, ada, post, "Thanks")  # authors may reply on their own posts

    page = await listing(client, post)

    assert [c["body"] for c in page["items"]] == ["First!", "Thanks"]
    assert page["items"][0]["author"] == {"username": "bob", "display_name": "Bob"}
    assert set(page["items"][0]) == {"id", "body", "author", "is_deleted", "edited", "created_at"}
    assert page["total"] == 2
    assert (await client.get(f"{POSTS}/{post['slug']}")).json()["comment_count"] == 2


async def test_comments_are_paginated(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)
    for body in ("one", "two", "three"):
        await comment(client, ada, post, body)

    page = await listing(client, post, params={"limit": 2, "offset": 2})

    assert [c["body"] for c in page["items"]] == ["three"]
    assert page["total"] == 3


async def test_drafts_cannot_be_commented_on(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    draft = await create_post(client, ada)
    url = f"{POSTS}/{draft['id']}/comments"

    assert (await client.post(url, json={"body": "Hi"}, headers=bob)).status_code == 404
    assert (await client.get(url)).status_code == 404
    assert (await client.post(url, json={"body": "Hi"}, headers=ada)).status_code == 409


async def test_commenting_requires_sign_in(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)

    response = await client.post(f"{POSTS}/{post['id']}/comments", json={"body": "Hi"})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [{"body": ""}, {"body": "   "}, {"body": "x" * 5001}, {"body": "Hi", "author_id": "x"}, {}],
    ids=["empty", "blank", "too-long", "extra-field", "missing"],
)
async def test_invalid_comments_are_rejected(client: AsyncClient, payload: dict[str, str]) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)

    response = await client.post(f"{POSTS}/{post['id']}/comments", json=payload, headers=ada)

    assert response.status_code == 422


# ─── Editing ──────────────────────────────────────────────


async def test_only_the_author_can_edit_a_comment(client: AsyncClient, app: FastAPI) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    mod = await signed_in(client, "mod")
    await grant_role(app, "mod", "moderator")
    post = await create_post(client, ada, publish=True)
    created = await comment(client, bob, post)
    url = f"{COMMENTS}/{created['id']}"

    same = await client.patch(url, json={"body": "Nice post!"}, headers=bob)
    assert same.json()["edited"] is False  # unchanged text is not an edit

    edited = await client.patch(url, json={"body": "Great post!"}, headers=bob)
    assert edited.status_code == 200
    assert edited.json()["body"] == "Great post!" and edited.json()["edited"] is True

    for other in (ada, mod):  # not even the post's author or a moderator
        response = await client.patch(url, json={"body": "Changed"}, headers=other)
        assert response.status_code == 403


# ─── Deleting ─────────────────────────────────────────────


async def test_deleted_comment_leaves_a_placeholder(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    post = await create_post(client, ada, publish=True)
    created = await comment(client, bob, post, "Oops")
    await comment(client, ada, post, "Reply")
    url = f"{COMMENTS}/{created['id']}"

    assert (await client.delete(url, headers=bob)).status_code == 204

    first = (await listing(client, post))["items"][0]
    assert first == {**first, "body": None, "author": None, "is_deleted": True}
    assert "Oops" not in (await client.get(f"{POSTS}/{post['id']}/comments")).text
    assert (await client.get(f"{POSTS}/{post['slug']}")).json()["comment_count"] == 1
    assert (await client.patch(url, json={"body": "Back"}, headers=bob)).status_code == 404
    assert (await client.delete(url, headers=bob)).status_code == 404


async def test_who_can_delete_a_comment(client: AsyncClient, app: FastAPI) -> None:
    ada = await signed_in(client, "ada")  # post author
    bob = await signed_in(client, "bob")  # commenter
    cara = await signed_in(client, "cara")  # bystander
    mod = await signed_in(client, "mod")
    await grant_role(app, "mod", "moderator")
    post = await create_post(client, ada, publish=True)
    first, second = await comment(client, bob, post), await comment(client, bob, post)

    assert (await client.delete(f"{COMMENTS}/{first['id']}", headers=cara)).status_code == 403
    assert (await client.delete(f"{COMMENTS}/{first['id']}", headers=ada)).status_code == 204
    assert (await client.delete(f"{COMMENTS}/{second['id']}", headers=mod)).status_code == 204


async def test_unpublished_post_hides_its_comments(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    post = await create_post(client, ada, publish=True)
    created = await comment(client, bob, post)
    await client.post(f"{POSTS}/{post['id']}/unpublish", headers=ada)

    assert (await client.get(f"{POSTS}/{post['id']}/comments")).status_code == 404
    assert (await listing(client, post, headers=ada))["total"] == 1  # author still sees them
    edit = await client.patch(f"{COMMENTS}/{created['id']}", json={"body": "X"}, headers=bob)
    assert edit.status_code == 404


# ─── Abuse protection ─────────────────────────────────────


async def test_commenting_is_rate_limited_per_user(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)
    for i in range(10):
        await comment(client, ada, post, f"Comment {i}")

    response = await client.post(
        f"{POSTS}/{post['id']}/comments", json={"body": "One too many"}, headers=ada
    )

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
