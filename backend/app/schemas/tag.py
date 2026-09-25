"""Tag schemas."""

from pydantic import BaseModel


class TagCount(BaseModel):
    name: str
    post_count: int
