"""Fill the local database with deterministic demo data. Refuses to run in production.

Usage: uv run python -m scripts.seed [--users 7] [--posts-per-user 3] [--reset]
The curated authors, posts and comments in scripts/demo_content.py always go in first. Extra
users (beyond the curated authors) get Faker names and reuse the curated posts, which makes
a large dataset for query tuning: --users 500 --posts-per-user 20 (about 10k posts).
"""

import argparse
import asyncio
import re
import sys
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.slugs import slugify
from app.db.session import Database
from app.models import Comment, Like, Post, PostStatus, Role, Tag, User
from scripts.demo_content import PERSONAS, POSTS, TAGS, DemoPost, unwrap

SEED = 42
# "!" can never equal a real password hash, so seeded accounts cannot log in.
UNUSABLE_PASSWORD = "!"  # noqa: S105
MAX_LIKES_PER_POST = 25  # keeps a large seed linear instead of users x posts


def make_personas(role: Role) -> list[User]:
    return [
        User(
            email=f"{persona.username}@example.com",
            username=persona.username,
            password_hash=UNUSABLE_PASSWORD,
            display_name=persona.display_name,
            bio=persona.bio,
            roles=[role],
        )
        for persona in PERSONAS
    ]


def make_extra_users(fake: Faker, count: int, role: Role) -> list[User]:
    users = []
    for i in range(count):
        base = re.sub(r"[^a-z0-9_]", "", fake.user_name().lower())[:24] or "user"
        username = f"{base}{i}"
        users.append(
            User(
                email=f"{username}@example.com",
                username=username,
                password_hash=UNUSABLE_PASSWORD,
                display_name=fake.name()[:60],
                bio=fake.sentence(nb_words=12)[:280],
                roles=[role],
            )
        )
    return users


def make_post(
    demo: DemoPost, author: User, tags: dict[str, Tag], slug: str, age: timedelta
) -> Post:
    return Post(
        author=author,
        title=demo.title,
        slug=slug,
        excerpt=demo.excerpt,
        content=unwrap(demo.content),
        status=PostStatus.DRAFT if demo.draft else PostStatus.PUBLISHED,
        published_at=None if demo.draft else datetime.now(UTC) - age,
        tags=[tags[name] for name in demo.tags],
    )


async def seed(session: AsyncSession, users_count: int, posts_per_user: int) -> None:
    fake = Faker()
    Faker.seed(SEED)

    role = (await session.execute(select(Role).where(Role.name == "user"))).scalar_one()
    tags = {name: Tag(name=name) for name in TAGS}
    personas = make_personas(role)
    by_username = {user.username: user for user in personas}
    extras = make_extra_users(fake, max(users_count - len(personas), 0), role)
    users = [*personas, *extras]

    curated = [
        (
            demo,
            make_post(
                demo,
                by_username[demo.author],
                tags,
                slugify(demo.title),
                timedelta(days=demo.days_ago, hours=fake.random_int(0, 12)),
            ),
        )
        for demo in POSTS
    ]
    published = [demo for demo in POSTS if not demo.draft]
    generated: list[Post] = []
    for i, author in enumerate(extras):
        for j in range(posts_per_user):
            demo = published[(i * posts_per_user + j) % len(published)]
            age = timedelta(minutes=fake.random_int(0, 90 * 24 * 60))
            generated.append(make_post(demo, author, tags, f"{slugify(demo.title)}-{i}-{j}", age))
    session.add_all([*tags.values(), *users, *(post for _, post in curated), *generated])
    await session.flush()

    # Likes and comments go in as multi-row INSERTs: one round trip per batch, not per row.
    likes: list[dict[str, object]] = []
    comments: list[dict[str, object]] = []
    for demo, post in curated:
        if demo.draft:
            continue
        others = [u for u in personas if u.id != post.author_id]  # nobody likes their own post
        liked_by = fake.random_sample(others, length=min(demo.likes, len(others)))
        likes += [{"user_id": fan.id, "post_id": post.id} for fan in liked_by]
        comments += [
            {"post_id": post.id, "author_id": by_username[username].id, "body": body}
            for username, body in demo.comments
        ]

    replies = [body for demo in published for _, body in demo.comments]
    for post in generated:
        others = [u for u in users if u.id != post.author_id]
        fans = fake.random_int(0, min(len(others), MAX_LIKES_PER_POST))
        likes += [
            {"user_id": fan.id, "post_id": post.id}
            for fan in fake.random_sample(others, length=fans)
        ]
        comments += [
            {
                "post_id": post.id,
                "author_id": fake.random_element(others).id,
                "body": fake.random_element(replies),
            }
            for _ in range(fake.random_int(0, 3))
        ]
    if likes:
        await session.execute(insert(Like), likes)
    if comments:
        await session.execute(insert(Comment), comments)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--users", type=int, default=len(PERSONAS), help="total users")
    parser.add_argument(
        "--posts-per-user", type=int, default=3, help="for users beyond the curated authors"
    )
    parser.add_argument("--reset", action="store_true", help="delete existing demo data first")
    args = parser.parse_args()

    settings = get_settings()
    if settings.is_production:
        print("Refusing to seed a production database.", file=sys.stderr)
        return 1

    db = Database(settings.database_url)
    try:
        async with db.sessionmaker() as session, session.begin():
            if args.reset:
                # Roles and permissions are reference data from migrations, so they stay.
                await session.execute(text("TRUNCATE users, tags RESTART IDENTITY CASCADE"))
            elif await session.scalar(select(func.count()).select_from(User)):
                print("Database already has users; use --reset to reseed.", file=sys.stderr)
                return 1
            await seed(session, args.users, args.posts_per_user)
    finally:
        await db.dispose()

    print(f"Seeded {max(args.users, len(PERSONAS))} users.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
