"""Comment schemas: plain-text bodies in, and public comment shapes out (deleted ones masked)."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.user import AuthorPublic

# Plain text, never HTML: clients render it escaped, so a comment cannot inject markup.
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: Body


class CommentUpdate(CommentCreate):
    pass


class CommentOut(BaseModel):
    """A deleted comment keeps its place in the thread but loses its body and author."""

    id: uuid.UUID
    body: str | None
    author: AuthorPublic | None
    is_deleted: bool
    edited: bool = Field(description="Changed after it was posted")
    created_at: datetime
