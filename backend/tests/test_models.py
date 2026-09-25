"""Database constraints: the schema itself rejects invalid or duplicate data."""

from datetime import UTC, datetime
from itertools import count

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment, Like, Post, PostStatus, Role, User

_ids = count()


def new_user(**overrides: object) -> User:
    n = next(_ids)
    values: dict[str, object] = {
        "email": f"user{n}@example.com",
        "username": f"user_{n}",
        "password_hash": "!",
        "display_name": f"User {n}",
        **overrides,
    }
    return User(**values)


def new_post(author: User, **overrides: object) -> Post:
    n = next(_ids)
    values: dict[str, object] = {
        "author": author,
        "title": f"Post {n}",
        "slug": f"post-{n}",
        "content": "Hello",
        **overrides,
    }
    return Post(**values)


async def test_reference_roles_are_seeded(db_session: AsyncSession) -> None:
    names = (await db_session.scalars(select(Role.name).order_by(Role.name))).all()

    assert names == ["moderator", "user"]


async def test_user_defaults_are_applied_by_the_database(db_session: AsyncSession) -> None:
    user = new_user()
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.is_active is True
    assert user.created_at is not None


@pytest.mark.parametrize("field", ["email", "username"])
async def test_email_and_username_are_unique(db_session: AsyncSession, field: str) -> None:
    first = new_user()
    db_session.add(first)
    await db_session.flush()

    db_session.add(new_user(**{field: getattr(first, field)}))
    with pytest.raises(IntegrityError, match=f"uq_users_{field}"):
        await db_session.flush()


@pytest.mark.parametrize(
    ("field", "value", "constraint"),
    [
        ("username", "Bad Name!", "ck_users_username_format"),
        ("username", "ab", "ck_users_username_format"),
        ("email", "Mixed@Example.com", "ck_users_email_lowercase"),
    ],
)
async def test_user_format_checks(
    db_session: AsyncSession, field: str, value: str, constraint: str
) -> None:
    db_session.add(new_user(**{field: value}))

    with pytest.raises(IntegrityError, match=constraint):
        await db_session.flush()


async def test_published_post_requires_published_at(db_session: AsyncSession) -> None:
    db_session.add(new_post(new_user(), status=PostStatus.PUBLISHED, published_at=None))

    with pytest.raises(IntegrityError, match="ck_posts_published_has_date"):
        await db_session.flush()


async def test_post_defaults_to_draft(db_session: AsyncSession) -> None:
    post = new_post(new_user())
    db_session.add(post)
    await db_session.flush()

    assert post.status is PostStatus.DRAFT


async def test_duplicate_like_is_rejected(db_session: AsyncSession) -> None:
    author, fan = new_user(), new_user()
    post = new_post(author, status=PostStatus.PUBLISHED, published_at=datetime.now(UTC))
    db_session.add_all([author, fan, post])
    await db_session.flush()

    db_session.add(Like(user_id=fan.id, post_id=post.id))
    await db_session.flush()
    db_session.expunge_all()  # forget the first Like so the ORM really sends a second INSERT
    db_session.add(Like(user_id=fan.id, post_id=post.id))

    with pytest.raises(IntegrityError, match="pk_likes"):
        await db_session.flush()


async def test_empty_comment_is_rejected(db_session: AsyncSession) -> None:
    author = new_user()
    post = new_post(author)
    db_session.add_all([author, post])
    await db_session.flush()

    db_session.add(Comment(post_id=post.id, author_id=author.id, body=""))
    with pytest.raises(IntegrityError, match="ck_comments_body_length"):
        await db_session.flush()


async def test_deleting_a_user_cascades_to_their_content(db_session: AsyncSession) -> None:
    author, fan = new_user(), new_user()
    post = new_post(author)
    db_session.add_all([author, fan, post])
    await db_session.flush()
    db_session.add_all(
        [
            Like(user_id=fan.id, post_id=post.id),
            Comment(post_id=post.id, author_id=fan.id, body="Nice"),
        ]
    )
    await db_session.flush()

    # A Core DELETE proves the database's ON DELETE CASCADE works, not the ORM's.
    await db_session.execute(delete(User).where(User.id == author.id))

    for model in (Post, Like, Comment):
        remaining = await db_session.scalar(select(func.count()).select_from(model))
        assert remaining == 0
