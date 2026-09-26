"""Post lifecycle: draft privacy, publishing, ownership, moderator deletes and slugs."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.repositories import posts as post_repo
from tests.conftest import create_post, grant_role, signed_in

POSTS = "/api/v1/posts"

PUBLIC_POST_FIELDS = {
    "id",
    "slug",
    "title",
    "excerpt",
    "content",
    "status",
    "author",
    "tags",
    "like_count",
    "comment_count",
    "liked_by_me",
    "published_at",
    "created_at",
    "updated_at",
}


# ─── Visibility ───────────────────────────────────────────


async def test_new_post_is_a_draft_only_its_author_can_see(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")

    response = await client.post(POSTS, json={"title": "Hi", "content": "Draft"}, headers=ada)
    post = response.json()

    assert response.status_code == 201
    assert response.headers["location"] == f"{POSTS}/{post['slug']}"
    assert post["status"] == "draft" and post["published_at"] is None
    assert (await client.get(f"{POSTS}/{post['slug']}", headers=ada)).status_code == 200
    assert (await client.get(f"{POSTS}/{post['slug']}")).status_code == 404
    assert (await client.get(f"{POSTS}/{post['slug']}", headers=bob)).status_code == 404
    assert (await client.get(POSTS)).json()["total"] == 0


async def test_published_post_is_public_and_exposes_no_private_fields(
    client: AsyncClient,
) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)

    response = await client.get(f"{POSTS}/{post['slug']}")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "published" and body["published_at"] is not None
    assert set(body) == PUBLIC_POST_FIELDS
    assert body["author"] == {"username": "ada", "display_name": "Ada"}
    assert "@" not in response.text  # no email anywhere


async def test_unpublish_hides_the_post_again(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)

    response = await client.post(f"{POSTS}/{post['id']}/unpublish", headers=ada)

    assert response.json()["status"] == "draft"
    assert response.json()["published_at"] == post["published_at"]  # first publication kept
    assert (await client.get(f"{POSTS}/{post['slug']}")).status_code == 404


async def test_publish_is_idempotent(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)

    again = await client.post(f"{POSTS}/{post['id']}/publish", headers=ada)

    assert again.status_code == 200
    assert again.json()["published_at"] == post["published_at"]


async def test_deleted_post_disappears_everywhere(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, publish=True)

    assert (await client.delete(f"{POSTS}/{post['id']}", headers=ada)).status_code == 204

    assert (await client.get(f"{POSTS}/{post['slug']}", headers=ada)).status_code == 404
    assert (await client.get(POSTS)).json()["total"] == 0
    assert (await client.get("/api/v1/users/me/posts", headers=ada)).json()["total"] == 0
    edit = await client.patch(f"{POSTS}/{post['id']}", json={"title": "X"}, headers=ada)
    assert edit.status_code == 404


# ─── Ownership ────────────────────────────────────────────


async def test_others_cannot_change_a_published_post(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    post = await create_post(client, ada, publish=True)
    url = f"{POSTS}/{post['id']}"

    attempts = [
        await client.patch(url, json={"title": "Hacked"}, headers=bob),
        await client.post(f"{url}/unpublish", headers=bob),
        await client.delete(url, headers=bob),
    ]

    assert [r.status_code for r in attempts] == [403, 403, 403]
    assert (await client.get(f"{POSTS}/{post['slug']}")).json()["title"] == post["title"]


async def test_others_get_404_for_a_draft_so_it_stays_secret(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    bob = await signed_in(client, "bob")
    post = await create_post(client, ada)
    url = f"{POSTS}/{post['id']}"

    attempts = [
        await client.patch(url, json={"title": "Hacked"}, headers=bob),
        await client.post(f"{url}/publish", headers=bob),
        await client.delete(url, headers=bob),
    ]

    assert [r.status_code for r in attempts] == [404, 404, 404]


async def test_moderator_can_delete_but_not_edit(client: AsyncClient, app: FastAPI) -> None:
    ada = await signed_in(client, "ada")
    mod = await signed_in(client, "mod")
    await grant_role(app, "mod", "moderator")
    post = await create_post(client, ada, publish=True)
    url = f"{POSTS}/{post['id']}"

    assert (await client.patch(url, json={"title": "X"}, headers=mod)).status_code == 403
    assert (await client.delete(url, headers=mod)).status_code == 204
    assert (await client.get(f"{POSTS}/{post['slug']}")).status_code == 404


async def test_writing_requires_sign_in(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada)
    url = f"{POSTS}/{post['id']}"

    attempts = [
        await client.post(POSTS, json={"title": "T", "content": "C"}),
        await client.patch(url, json={"title": "X"}),
        await client.post(f"{url}/publish"),
        await client.delete(url),
    ]

    assert [r.status_code for r in attempts] == [401, 401, 401, 401]


@pytest.mark.parametrize(
    "extra",
    [{"author_id": "00000000-0000-0000-0000-000000000000"}, {"status": "published"}, {"slug": "x"}],
    ids=["author_id", "status", "slug"],
)
async def test_server_controlled_fields_cannot_be_sent(
    client: AsyncClient, extra: dict[str, str]
) -> None:
    ada = await signed_in(client, "ada")

    response = await client.post(POSTS, json={"title": "T", "content": "C", **extra}, headers=ada)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [{}, {"title": None}, {"content": None}, {"tags": None}, {"title": "   "}],
    ids=["empty", "null-title", "null-content", "null-tags", "blank-title"],
)
async def test_invalid_updates_are_rejected(
    client: AsyncClient, payload: dict[str, object]
) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada)

    response = await client.patch(f"{POSTS}/{post['id']}", json=payload, headers=ada)

    assert response.status_code == 422


async def test_update_changes_only_sent_fields(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, excerpt="Custom", tags=["python"])

    response = await client.patch(
        f"{POSTS}/{post['id']}", json={"content": "New body", "tags": ["go"]}, headers=ada
    )
    body = response.json()

    assert body["content"] == "New body"
    assert body["tags"] == ["go"]
    assert body["title"] == post["title"] and body["excerpt"] == "Custom"


# ─── Excerpts & tags ──────────────────────────────────────


async def test_excerpt_defaults_to_the_start_of_the_content(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    content = "word " * 100
    await create_post(client, ada, publish=True, content=content)

    item = (await client.get(POSTS)).json()["items"][0]

    assert item["excerpt"] == content[:280]
    assert "content" not in item  # lists stay small


async def test_tags_are_normalised_and_deduplicated(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")

    post = await create_post(client, ada, tags=["Python", "python", " fastapi "])

    assert post["tags"] == ["fastapi", "python"]


@pytest.mark.parametrize(
    "tags",
    [["a", "b", "c", "d", "e", "f"], ["no spaces"], ["x" * 41]],
    ids=["too-many", "bad-format", "too-long"],
)
async def test_invalid_tags_are_rejected(client: AsyncClient, tags: list[str]) -> None:
    ada = await signed_in(client, "ada")

    response = await client.post(
        POSTS, json={"title": "T", "content": "C", "tags": tags}, headers=ada
    )

    assert response.status_code == 422


# ─── Slugs ────────────────────────────────────────────────


async def test_same_title_gets_a_unique_slug(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")

    first = await create_post(client, ada, title="Hello World")
    second = await create_post(client, ada, title="Hello World")

    assert first["slug"] == "hello-world"
    assert second["slug"].startswith("hello-world-") and second["slug"] != first["slug"]


async def test_retitling_a_draft_updates_its_slug(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, title="First idea")

    response = await client.patch(f"{POSTS}/{post['id']}", json={"title": "Better"}, headers=ada)

    assert response.json()["slug"] == "better"


async def test_slug_is_frozen_once_published(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    post = await create_post(client, ada, title="Launch day", publish=True)
    await client.post(f"{POSTS}/{post['id']}/unpublish", headers=ada)

    response = await client.patch(f"{POSTS}/{post['id']}", json={"title": "Renamed"}, headers=ada)

    assert response.json()["title"] == "Renamed"
    assert response.json()["slug"] == "launch-day"  # old links keep working


async def test_slug_race_is_resolved_by_the_unique_constraint(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate two requests passing the pre-check at once: the database must break the tie."""
    ada = await signed_in(client, "ada")
    taken = await create_post(client, ada, title="Race")
    draft = await create_post(client, ada, title="Other")

    async def never_taken(*args: object) -> bool:
        return False

    monkeypatch.setattr(post_repo, "slug_taken", never_taken)
    created = await create_post(client, ada, title="Race")
    renamed = await client.patch(f"{POSTS}/{draft['id']}", json={"title": "Race"}, headers=ada)

    assert created["slug"].startswith("race-")
    assert renamed.status_code == 200
    assert renamed.json()["slug"].startswith("race-")
    assert len({taken["slug"], created["slug"], renamed.json()["slug"]}) == 3
