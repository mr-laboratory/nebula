"""Index usage: each hot query can be served by its index, including under a generic plan.

The test database gets 10k posts (rolled back afterwards) and sequential
scans are switched off: the question is whether the planner *can* use the index for the SQL
the repositories really send, not whether it would on a table this small.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import comments, posts
from app.schemas.post import MyPostFilters, PostFilters

Call = Callable[[AsyncSession], Awaitable[object]]


def scans(plan: dict[str, Any]) -> set[str]:
    found = {plan["Index Name"]} if "Index Name" in plan else set()
    for child in plan.get("Plans", []):
        found |= scans(child)
    return found


async def captured(session: AsyncSession, call: Call) -> list[tuple[str, Any]]:
    statements: list[tuple[str, Any]] = []

    def record(conn: object, cursor: object, statement: str, params: Any, *args: object) -> None:
        statements.append((statement, params))

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", record)
    try:
        await call(session)
    finally:
        event.remove(bind, "before_cursor_execute", record)
    return statements


@pytest.fixture
async def posts_table(db_session: AsyncSession) -> AsyncSession:
    """Realistic planner statistics: published posts whose titles never contain the term."""
    author = await db_session.scalar(
        text(
            "INSERT INTO users (email, username, password_hash, display_name) "
            "VALUES ('plans@example.com', 'plans', '!', 'Plans') RETURNING id"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO posts (author_id, title, slug, excerpt, content, status, published_at) "
            "SELECT :author, 'Post number ' || i, 'post-' || i, 'Excerpt ' || i, 'Body', "
            "'published', now() - i * interval '1 minute' FROM generate_series(1, 10000) i"
        ),
        {"author": author},
    )
    await db_session.execute(text("ANALYZE posts"))
    return db_session


async def indexes_used(session: AsyncSession, call: Call) -> set[str]:
    conn = await session.connection()
    await conn.exec_driver_sql("SET LOCAL enable_seqscan = off")
    used: set[str] = set()
    for statement, params in await captured(session, call):
        result = await conn.exec_driver_sql(f"EXPLAIN (FORMAT JSON) {statement}", params)
        used |= scans(result.scalar_one()[0]["Plan"])
    return used


SOMEONE = uuid.uuid4()

CASES: dict[str, tuple[Call, set[str]]] = {
    "feed": (
        lambda s: posts.list_public(s, PostFilters(), None),
        {"ix_posts_feed", "ix_likes_post_id", "ix_comments_post_created"},
    ),
    "feed oldest": (
        lambda s: posts.list_public(s, PostFilters(sort="oldest"), None),
        {"ix_posts_feed"},
    ),
    "tag filter": (
        lambda s: posts.list_public(s, PostFilters(tag="python"), None),
        {"ix_post_tags_tag_id"},
    ),
    "search": (
        lambda s: posts.list_public(s, PostFilters(q="nebula"), None),
        {"ix_posts_title_trgm", "ix_posts_excerpt_trgm"},
    ),
    "dashboard": (
        lambda s: posts.list_by_author(s, SOMEONE, MyPostFilters()),
        {"ix_posts_author_updated"},
    ),
    "comments": (
        lambda s: comments.list_for_post(s, SOMEONE, 20, 0),
        {"ix_comments_post_created"},
    ),
}


@pytest.mark.parametrize("case", CASES)
async def test_hot_query_can_use_its_index(posts_table: AsyncSession, case: str) -> None:
    call, expected = CASES[case]
    assert expected <= await indexes_used(posts_table, call)


async def test_feed_uses_partial_index_under_a_generic_plan(db_session: AsyncSession) -> None:
    """Prepared statements may switch to a generic plan that cannot see parameter values.

    The partial index's `status = 'published'` must therefore be literal SQL in the query:
    with a bound $1 the planner could no longer prove the index applies.
    """
    feed = await captured(db_session, lambda s: posts.list_public(s, PostFilters(), None))
    statement, params = next((sql, p) for sql, p in feed if "ORDER BY" in sql)
    assert "posts.status = 'published'" in statement

    conn = await db_session.connection()
    await conn.exec_driver_sql("SET LOCAL enable_seqscan = off")
    await conn.exec_driver_sql("SET LOCAL plan_cache_mode = force_generic_plan")
    await conn.exec_driver_sql(f"PREPARE feed_page AS {statement}")
    try:
        args = ", ".join(str(p) for p in params)  # page size and offsets: plain integers
        result = await conn.execute(text(f"EXPLAIN (FORMAT JSON) EXECUTE feed_page({args})"))
        assert "ix_posts_feed" in scans(result.scalar_one()[0]["Plan"])
    finally:
        await conn.exec_driver_sql("DEALLOCATE feed_page")
