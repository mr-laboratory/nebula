"""Discovery: the public feed (pagination, filters, sorting), my posts, tags and author profiles."""

import pytest
from httpx import AsyncClient

from tests.conftest import create_post, signed_in

POSTS = "/api/v1/posts"


async def titles(client: AsyncClient, **params: str | int) -> list[str]:
    response = await client.get(POSTS, params=params)
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


# ─── Pagination & sorting ─────────────────────────────────


async def test_feed_is_paginated_newest_first(client: AsyncClient) -> None:
    ada = await signed_in(client)
    for title in ("one", "two", "three"):
        await create_post(client, ada, title=title, publish=True)

    first = (await client.get(POSTS, params={"limit": 2})).json()
    second = (await client.get(POSTS, params={"limit": 2, "offset": 2})).json()

    assert [p["title"] for p in first["items"]] == ["three", "two"]
    assert [p["title"] for p in second["items"]] == ["one"]
    assert first["total"] == second["total"] == 3
    assert (first["limit"], second["offset"]) == (2, 2)
    assert await titles(client, sort="oldest") == ["one", "two", "three"]


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"sort": "title"}, {"order_by": "id"}],
    ids=["limit-zero", "limit-too-big", "negative-offset", "unknown-sort", "unknown-param"],
)
async def test_invalid_feed_parameters_are_rejected(
    client: AsyncClient, params: dict[str, str | int]
) -> None:
    assert (await client.get(POSTS, params=params)).status_code == 422


async def test_feed_query_count_does_not_grow_with_page_size(
    client: AsyncClient, sql_statements: list[str]
) -> None:
    """No N+1: authors, tags, like and comment counts are loaded for the whole page at once."""
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    first = await create_post(client, ada, publish=True, tags=["a", "b"])
    await client.put(f"{POSTS}/{first['id']}/like", headers=bob)

    async def statements_for_feed(headers: dict[str, str] | None = None) -> int:
        sql_statements.clear()
        assert (await client.get(POSTS, headers=headers)).status_code == 200
        return len(sql_statements)

    anonymous, signed = await statements_for_feed(), await statements_for_feed(headers=bob)

    for i in range(5):
        post = await create_post(client, bob if i % 2 else ada, publish=True, tags=[f"t{i}"])
        await client.put(f"{POSTS}/{post['id']}/like", headers=bob if i % 2 == 0 else ada)
        await client.post(f"{POSTS}/{post['id']}/comments", json={"body": "Hi"}, headers=bob)

    assert await statements_for_feed() == anonymous == 3  # count, posts+authors+counts, tags
    assert await statements_for_feed(headers=bob) == signed == 4  # + loading the viewer


# ─── Filters ──────────────────────────────────────────────


async def test_feed_filters_by_tag_author_and_search(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    await create_post(client, ada, title="Async Python", tags=["python"], publish=True)
    await create_post(client, bob, title="React hooks", tags=["react"], publish=True)
    await create_post(client, bob, title="Python drafts", tags=["python"])  # draft: hidden

    assert await titles(client, tag="PYTHON") == ["Async Python"]
    assert await titles(client, author="bob") == ["React hooks"]
    assert await titles(client, q="hooks") == ["React hooks"]
    assert await titles(client, q="python", author="bob") == []
    assert await titles(client, tag="unknown") == []


async def test_search_treats_wildcards_literally(client: AsyncClient) -> None:
    ada = await signed_in(client)
    await create_post(client, ada, title="100% coverage", publish=True)
    await create_post(client, ada, title="Plain title", publish=True)

    assert await titles(client, q="%") == ["100% coverage"]
    assert await titles(client, q="_") == []


# ─── My posts ─────────────────────────────────────────────


async def test_my_posts_include_drafts_and_only_mine(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    await create_post(client, ada, title="Ada draft")
    await create_post(client, ada, title="Ada live", publish=True)
    await create_post(client, bob, title="Bob live", publish=True)

    mine = (await client.get("/api/v1/users/me/posts", headers=ada)).json()
    drafts = (
        await client.get("/api/v1/users/me/posts", params={"status": "draft"}, headers=ada)
    ).json()

    assert {p["title"] for p in mine["items"]} == {"Ada draft", "Ada live"}
    assert [p["title"] for p in drafts["items"]] == ["Ada draft"]
    assert (await client.get("/api/v1/users/me/posts")).status_code == 401


# ─── Tags & profiles ──────────────────────────────────────


async def test_tags_count_only_public_posts(client: AsyncClient) -> None:
    ada = await signed_in(client)
    await create_post(client, ada, tags=["python", "web"], publish=True)
    await create_post(client, ada, tags=["python"], publish=True)
    await create_post(client, ada, tags=["secret"])  # draft

    response = await client.get("/api/v1/tags")

    assert response.json() == [
        {"name": "python", "post_count": 2},
        {"name": "web", "post_count": 1},
    ]


async def test_public_profile_hides_private_data(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    await create_post(client, ada, publish=True)
    await create_post(client, ada)  # draft: not counted

    response = await client.get("/api/v1/users/ADA")
    body = response.json()

    assert response.status_code == 200
    assert set(body) == {"username", "display_name", "bio", "created_at", "post_count"}
    assert body["post_count"] == 1
    assert (await client.get("/api/v1/users/nobody")).status_code == 404
