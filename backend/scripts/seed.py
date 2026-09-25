"""Fill the local database with deterministic demo data. Refuses to run in production.

Usage: uv run python -m scripts.seed [--users 10] [--posts-per-user 3] [--reset]
"""

import argparse
import asyncio
import re
import sys
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import Database
from app.models import Comment, Like, Post, PostStatus, Role, Tag, User

SEED = 42
TAGS = ["python", "fastapi", "react", "postgres", "design", "devops", "security", "career"]
# "!" can never equal a real password hash, so seeded accounts cannot log in.
UNUSABLE_PASSWORD = "!"  # noqa: S105


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def make_users(fake: Faker, count: int, role: Role) -> list[User]:
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


def make_post(fake: Faker, author: User, tags: list[Tag], index: int) -> Post:
    title = fake.sentence(nb_words=6).rstrip(".")
    published = fake.boolean(chance_of_getting_true=80)
    paragraphs = "\n\n".join(fake.paragraphs(nb=fake.random_int(3, 6)))
    return Post(
        author=author,
        title=title,
        slug=f"{slugify(title)[:200]}-{index}",
        excerpt=fake.sentence(nb_words=20)[:300],
        content=f"## {fake.sentence(nb_words=4)}\n\n{paragraphs}",
        status=PostStatus.PUBLISHED if published else PostStatus.DRAFT,
        published_at=(
            datetime.now(UTC) - timedelta(days=fake.random_int(0, 90)) if published else None
        ),
        tags=fake.random_sample(tags, length=fake.random_int(1, 3)),
    )


async def seed(session: AsyncSession, users_count: int, posts_per_user: int) -> None:
    fake = Faker()
    Faker.seed(SEED)

    role = (await session.execute(select(Role).where(Role.name == "user"))).scalar_one()
    tags = [Tag(name=name) for name in TAGS]
    users = make_users(fake, users_count, role)
    posts = [
        make_post(fake, author, tags, i * posts_per_user + j)
        for i, author in enumerate(users)
        for j in range(posts_per_user)
    ]
    session.add_all([*tags, *users, *posts])
    await session.flush()

    for post in (p for p in posts if p.status is PostStatus.PUBLISHED):
        others = [u for u in users if u.id != post.author_id]  # nobody likes their own post
        for fan in fake.random_sample(others, length=fake.random_int(0, len(others))):
            session.add(Like(user_id=fan.id, post_id=post.id))
        for _ in range(fake.random_int(0, 4)):
            commenter = fake.random_element(others)
            session.add(Comment(post_id=post.id, author_id=commenter.id, body=fake.paragraph()))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--posts-per-user", type=int, default=3)
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

    print(f"Seeded {args.users} users with {args.posts_per_user} posts each.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
