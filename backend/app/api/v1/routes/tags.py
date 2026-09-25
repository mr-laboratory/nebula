"""Tag endpoints: tags in use, for filters and tag clouds."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.repositories import tags as tag_repo
from app.schemas.tag import TagCount

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", summary="Tags used by published posts, most used first")
async def list_tags(
    session: SessionDep, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> list[TagCount]:
    rows = await tag_repo.list_in_use(session, limit)
    return [TagCount(name=name, post_count=count) for name, count in rows]
