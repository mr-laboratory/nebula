"""Slug generation: readable, URL-safe and never empty."""

import re

import pytest

from app.core.slugs import SLUG_MAX_LENGTH, slugify, with_suffix


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Hello, World!", "hello-world"),
        ("  Café  crème brûlée ", "cafe-creme-brulee"),
        ("FastAPI + Postgres = ❤️", "fastapi-postgres"),
        ("already-a-slug", "already-a-slug"),
        ("日本語", "post"),  # no Latin letters or digits
        ("!!!", "post"),
    ],
)
def test_slugify(title: str, expected: str) -> None:
    assert slugify(title) == expected


def test_long_titles_are_truncated_without_a_trailing_hyphen() -> None:
    slug = slugify("word " * 50)

    assert len(slug) <= SLUG_MAX_LENGTH
    assert not slug.endswith("-")


def test_suffix_is_random_and_url_safe() -> None:
    first, second = with_suffix("hello"), with_suffix("hello")

    assert first != second
    assert re.fullmatch(r"hello-[0-9a-f]{6}", first)
