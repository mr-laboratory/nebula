"""HTTP caching and compression: ETag/304 for anonymous public reads, no-store otherwise, gzip."""

from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.core.middleware import CompressionMiddleware
from tests.conftest import create_post, signed_in

POSTS = "/api/v1/posts"


async def test_public_read_has_etag_and_revalidates(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    await create_post(client, ada, publish=True)

    first = await client.get(POSTS)
    etag = first.headers["ETag"]
    assert etag.startswith('W/"')
    assert first.headers["Cache-Control"] == "no-cache"
    assert "Authorization" in first.headers["Vary"]

    cached = await client.get(POSTS, headers={"If-None-Match": etag})
    assert cached.status_code == 304
    assert cached.content == b""
    assert cached.headers["ETag"] == etag
    assert "X-Request-ID" in cached.headers  # outer middleware still runs
    assert cached.headers["X-Content-Type-Options"] == "nosniff"


async def test_etag_changes_when_the_content_does(client: AsyncClient) -> None:
    ada, bob = await signed_in(client, "ada"), await signed_in(client, "bob")
    post = await create_post(client, ada, publish=True)
    etag = (await client.get(f"{POSTS}/{post['slug']}")).headers["ETag"]

    await client.put(f"{POSTS}/{post['id']}/like", headers=bob)

    fresh = await client.get(f"{POSTS}/{post['slug']}", headers={"If-None-Match": etag})
    assert fresh.status_code == 200
    assert fresh.json()["like_count"] == 1
    assert fresh.headers["ETag"] != etag


async def test_signed_in_reads_are_never_stored(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    for path in (POSTS, "/api/v1/users/me", "/api/v1/users/me/posts"):
        response = await client.get(path, headers=ada)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert "ETag" not in response.headers


async def test_errors_and_writes_are_not_cached(client: AsyncClient) -> None:
    missing = await client.get(f"{POSTS}/no-such-post")
    assert missing.status_code == 404
    assert "ETag" not in missing.headers
    assert missing.headers["Cache-Control"] == "no-store"

    ada = await signed_in(client, "ada")
    created = await client.post(POSTS, json={"title": "T", "content": "C"}, headers=ada)
    assert "ETag" not in created.headers


async def test_large_responses_are_gzipped(client: AsyncClient) -> None:
    ada = await signed_in(client, "ada")
    for i in range(3):
        await create_post(client, ada, publish=True, title=f"Post {i}", excerpt="x" * 250)

    response = await client.get(POSTS, headers={"Accept-Encoding": "gzip"})
    assert response.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in response.headers["Vary"]
    assert len(response.json()["items"]) == 3  # httpx decompressed it transparently


async def test_auth_responses_are_never_compressed() -> None:
    """Tokens next to attacker-influenced input must not be compressed (BREACH)."""

    async def big(request: object) -> PlainTextResponse:
        return PlainTextResponse("token " * 500)

    inner = Starlette(routes=[Route("/api/v1/auth/login", big), Route("/api/v1/posts", big)])
    app = CompressionMiddleware(inner, skip_paths=("/api/v1/auth",))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as ac:
        auth = await ac.get("/api/v1/auth/login", headers={"Accept-Encoding": "gzip"})
        other = await ac.get("/api/v1/posts", headers={"Accept-Encoding": "gzip"})
    assert "Content-Encoding" not in auth.headers
    assert other.headers["Content-Encoding"] == "gzip"
