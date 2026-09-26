"""Like response: the post's new like count and whether the viewer likes it."""

from pydantic import BaseModel


class LikeStatus(BaseModel):
    like_count: int
    liked_by_me: bool
