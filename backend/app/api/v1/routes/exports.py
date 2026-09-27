"""Export endpoints: download my posts as Word or PDF, one post or all of them."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, RedisDep, SessionDep
from app.core.rate_limit import enforce
from app.services import exports
from app.services.exports import MEDIA_TYPES, ExportFile, ExportFormat

router = APIRouter(prefix="/exports", tags=["exports"])

EXPORT_LIMIT = {"limit": 10, "window": 3600}
FILE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {"content": {media: {} for media in MEDIA_TYPES.values()}}
}
Format = Annotated[ExportFormat, Query(alias="format")]


def _download(file: ExportFile) -> StreamingResponse:
    return StreamingResponse(
        file.chunks(),
        media_type=file.media_type,
        headers={
            # Filenames are built from slugs and usernames, which are already URL-safe.
            "Content-Disposition": f'attachment; filename="{file.filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get(
    "/posts",
    summary="Download all my posts (drafts included) as one document",
    response_class=StreamingResponse,
    responses=FILE_RESPONSE,
)
async def export_my_posts(
    fmt: Format, user: CurrentUser, session: SessionDep, redis: RedisDep
) -> StreamingResponse:
    """A cover page and contents list, then each post on a new page. Deleted posts are left out."""
    await enforce(redis, "export:user", str(user.id), **EXPORT_LIMIT)
    return _download(await exports.export_all(session, user, fmt))


@router.get(
    "/posts/{slug}",
    summary="Download one of my posts",
    response_class=StreamingResponse,
    responses=FILE_RESPONSE,
)
async def export_my_post(
    slug: Annotated[str, Path(max_length=220)],
    fmt: Format,
    user: CurrentUser,
    session: SessionDep,
    redis: RedisDep,
) -> StreamingResponse:
    """Only the author can export a post; anyone else gets 404."""
    await enforce(redis, "export:user", str(user.id), **EXPORT_LIMIT)
    return _download(await exports.export_one(session, user, slug, fmt))
