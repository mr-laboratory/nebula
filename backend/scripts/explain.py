"""Run the hot read paths and print EXPLAIN ANALYZE timings and scan types for their SQL.

Usage (after `make seed-large`): uv run python -m scripts.explain
Each scenario calls the real repository function, records the statements it sends, then
re-runs each one under EXPLAIN (ANALYZE, BUFFERS) and reports the median of several runs.
"""

import asyncio
import statistics
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import Database
from app.models import Post, PostStatus, User
from app.repositories import comments, posts
from app.schemas.post import MyPostFilters, PostFilters

RUNS = 7
Scenario = Callable[[AsyncSession], Awaitable[object]]


def scan_nodes(plan: dict[str, Any]) -> list[str]:
    """Every scan in a plan tree, e.g. 'Seq Scan posts' or 'Index Scan ix_posts_feed'."""
    found = []
    if "Scan" in plan["Node Type"]:
        target = plan.get("Index Name") or plan.get("Relation Name", "")
        found.append(f"{plan['Node Type']} {target}".strip())
    for child in plan.get("Plans", []):
        found += scan_nodes(child)
    return found


async def measure(session: AsyncSession, name: str, scenario: Scenario) -> None:
    captured: list[tuple[str, Any]] = []

    def record(conn: object, cursor: object, statement: str, params: Any, *args: object) -> None:
        captured.append((statement, params))

    engine = session.get_bind()  # the sync Engine behind the async session
    event.listen(engine, "before_cursor_execute", record)
    try:
        await scenario(session)
    finally:
        event.remove(engine, "before_cursor_execute", record)

    conn = await session.connection()
    total_ms = 0.0
    scans: list[str] = []
    for statement, params in captured:
        timings = []
        for _ in range(RUNS):
            result = await conn.exec_driver_sql(
                f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}", params
            )
            report = result.scalar_one()[0]
            timings.append(report["Planning Time"] + report["Execution Time"])
        total_ms += statistics.median(timings)
        scans += [s for s in scan_nodes(report["Plan"]) if s not in scans]
    print(f"| {name} | {len(captured)} | {total_ms:.2f} | {', '.join(scans)} |")


async def post_page(session: AsyncSession, post: Post) -> None:
    await posts.get_by_slug(session, post.slug)
    await posts.get_stats(session, post.id, None)


async def run(session: AsyncSession) -> None:
    await session.execute(text("ANALYZE"))  # fresh planner statistics after seeding
    author = (await session.execute(select(User).limit(1))).scalar_one()
    post = (
        await session.execute(
            select(Post).where(Post.status == PostStatus.PUBLISHED).order_by(Post.slug).limit(1)
        )
    ).scalar_one()
    word = post.title.split()[1].lower()
    counts = await session.execute(
        text(
            "SELECT (SELECT count(*) FROM posts), (SELECT count(*) FROM likes), "
            "(SELECT count(*) FROM comments)"
        )
    )
    n_posts, n_likes, n_comments = counts.one()
    print(f"Dataset: {n_posts} posts, {n_likes} likes, {n_comments} comments\n")

    scenarios: dict[str, Scenario] = {
        "Feed, newest (page 1)": lambda s: posts.list_public(s, PostFilters(), None),
        "Feed, signed-in viewer": lambda s: posts.list_public(s, PostFilters(), author.id),
        "Feed, oldest": lambda s: posts.list_public(s, PostFilters(sort="oldest"), None),
        "Feed, deep page (offset 5000)": lambda s: posts.list_public(
            s, PostFilters(offset=5000), None
        ),
        "Feed, tag filter": lambda s: posts.list_public(s, PostFilters(tag="postgres"), None),
        f"Search `q={word}`": lambda s: posts.list_public(s, PostFilters(q=word), None),
        "Search, no match": lambda s: posts.list_public(s, PostFilters(q="zzqx"), None),
        "Profile posts (author filter)": lambda s: posts.list_public(
            s, PostFilters(author=author.username), None
        ),
        "Dashboard (own posts)": lambda s: posts.list_by_author(s, author.id, MyPostFilters()),
        "Post page (slug + stats)": lambda s: post_page(s, post),
        "Comments for a post": lambda s: comments.list_for_post(s, post.id, 20, 0),
    }
    print("| Query | Statements | Time (ms) | Scans |\n|---|---|---|---|")
    for name, scenario in scenarios.items():
        await measure(session, name, scenario)


async def main() -> int:
    settings = get_settings()
    if settings.is_production:
        print("Refusing to run against production.", file=sys.stderr)
        return 1
    db = Database(settings.database_url)
    try:
        async with db.sessionmaker() as session:
            await run(session)
            await session.rollback()
    finally:
        await db.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
