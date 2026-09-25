"""Post schemas: create/update payloads, list filters, and public response shapes."""

import uuid
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models import PostStatus
from app.schemas.common import PageParams, lowercase
from app.schemas.user import AuthorPublic

MAX_TAGS = 5


def _unique(tags: list[str]) -> list[str]:
    return list(dict.fromkeys(tags))  # drop duplicates, keep the author's order


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Content = Annotated[str, Field(min_length=1, max_length=100_000)]
Excerpt = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
TagName = Annotated[str, BeforeValidator(lowercase), Field(pattern=r"^[a-z0-9-]{1,40}$")]
TagList = Annotated[list[TagName], Field(max_length=MAX_TAGS), AfterValidator(_unique)]


class PostCreate(BaseModel):
    """A new post always starts as a draft; author and slug are set by the server."""

    model_config = ConfigDict(extra="forbid")

    title: Title
    content: Content = Field(description="Markdown")
    excerpt: Excerpt | None = Field(default=None, description="Defaults to the content's start")
    tags: TagList = []


class PostUpdate(BaseModel):
    """Partial update: only the fields sent are changed. `tags` replaces the whole list."""

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    content: Content | None = None
    excerpt: Excerpt | None = None
    tags: TagList | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for field in ("title", "content", "tags"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class PostFilters(PageParams):
    """Public feed query. Sorting is a fixed choice, never a raw column name."""

    tag: Annotated[str, BeforeValidator(lowercase), Field(max_length=40)] | None = None
    author: Annotated[str, BeforeValidator(lowercase), Field(max_length=30)] | None = None
    q: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
        | None
    ) = Field(default=None, description="Case-insensitive search in title and excerpt")
    sort: Literal["newest", "oldest"] = "newest"


class MyPostFilters(PageParams):
    status: PostStatus | None = None


class PostSummary(BaseModel):
    """A post in a list. `content` is left out to keep pages small."""

    id: uuid.UUID
    slug: str
    title: str
    excerpt: str
    status: PostStatus
    author: AuthorPublic
    tags: list[str]
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PostDetail(PostSummary):
    content: str
