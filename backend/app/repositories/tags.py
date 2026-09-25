"""Tag queries: find-or-create by name (race-safe) and tags in use with their post counts."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Post, Tag, post_tags
from app.repositories.posts import IS_PUBLIC


async def get_or_create(session: AsyncSession, names: list[str]) -> list[Tag]:
    """Return a Tag for every name, in the given order, creating missing ones."""
    if not names:
        return []
    # ON CONFLICT DO NOTHING: two requests creating the same new tag can't collide.
    await session.execute(
        insert(Tag).values([{"name": name} for name in names]).on_conflict_do_nothing()
    )
    tags = {tag.name: tag for tag in await session.scalars(select(Tag).where(Tag.name.in_(names)))}
    return [tags[name] for name in names]


async def list_in_use(session: AsyncSession, limit: int) -> list[tuple[str, int]]:
    """Tags attached to at least one public post, most used first."""
    post_count = func.count(Post.id)
    stmt = (
        select(Tag.name, post_count)
        .join(post_tags, post_tags.c.tag_id == Tag.id)
        .join(Post, Post.id == post_tags.c.post_id)
        .where(*IS_PUBLIC)
        .group_by(Tag.id)
        .order_by(post_count.desc(), Tag.name)
        .limit(limit)
    )
    return [(name, count) for name, count in (await session.execute(stmt)).all()]
