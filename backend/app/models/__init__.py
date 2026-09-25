"""ORM models. Importing this package registers every table on Base.metadata (used by Alembic)."""

from app.models.comment import Comment
from app.models.like import Like
from app.models.post import Post, PostStatus
from app.models.refresh_token import RefreshToken
from app.models.role import Permission, Role, role_permissions, user_roles
from app.models.tag import Tag, post_tags
from app.models.user import User

__all__ = [
    "Comment",
    "Like",
    "Permission",
    "Post",
    "PostStatus",
    "RefreshToken",
    "Role",
    "Tag",
    "User",
    "post_tags",
    "role_permissions",
    "user_roles",
]
