"""Likes: idempotent like/unlike, no self-likes, drafts stay hidden, counts in post responses."""

import asyncio

from httpx import AsyncClient

from tests.conftest import create_post, signed_in

POSTS = "/api/v1/posts"


async def test_like_and_unlike_are_idempotent(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    post = await create_post(client, ada, publish=True)
    url = f"{POSTS}/{post['id']}/like"

    first, again = await client.put(url, headers=bob), await client.put(url, headers=bob)
    assert first.status_code == again.status_code == 200
    assert again.json() == {"like_count": 1, "liked_by_me": True}

    removed, again = await client.delete(url, headers=bob), await client.delete(url, headers=bob)
    assert removed.status_code == again.status_code == 200
    assert again.json() == {"like_count": 0, "liked_by_me": False}


async def test_concurrent_likes_count_once(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    post = await create_post(client, ada, publish=True)
    url = f"{POSTS}/{post['id']}/like"

    responses = await asyncio.gather(*(client.put(url, headers=bob) for _ in range(5)))

    assert {r.status_code for r in responses} == {200}
    assert (await client.get(f"{POSTS}/{post['slug']}")).json()["like_count"] == 1


async def test_counts_and_liked_by_me_in_post_responses(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    cara = await signed_in(client, "cara")
    post = await create_post(client, ada, publish=True)
    await client.put(f"{POSTS}/{post['id']}/like", headers=bob)

    def view(response_json: dict[str, object]) -> tuple[object, object]:
        return response_json["like_count"], response_json["liked_by_me"]

    detail = f"{POSTS}/{post['slug']}"
    assert view((await client.get(detail, headers=bob)).json()) == (1, True)
    assert view((await client.get(detail, headers=cara)).json()) == (1, False)
    assert view((await client.get(detail)).json()) == (1, None)
    assert view((await client.get(POSTS, headers=bob)).json()["items"][0]) == (1, True)
    assert view((await client.get(POSTS)).json()["items"][0]) == (1, None)


async def test_you_cannot_like_your_own_post(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)

    response = await client.put(f"{POSTS}/{post['id']}/like", headers=ada)

    assert response.status_code == 403


async def test_drafts_and_deleted_posts_cannot_be_liked(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    draft = await create_post(client, ada)
    gone = await create_post(client, ada, publish=True)
    await client.delete(f"{POSTS}/{gone['id']}", headers=ada)

    assert (await client.put(f"{POSTS}/{draft['id']}/like", headers=bob)).status_code == 404
    assert (await client.put(f"{POSTS}/{gone['id']}/like", headers=bob)).status_code == 404
    unknown = f"{POSTS}/00000000-0000-0000-0000-000000000000/like"
    assert (await client.put(unknown, headers=bob)).status_code == 404


async def test_liking_requires_sign_in(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)
    url = f"{POSTS}/{post['id']}/like"

    assert (await client.put(url)).status_code == 401
    assert (await client.delete(url)).status_code == 401
