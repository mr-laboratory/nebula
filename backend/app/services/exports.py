"""Exports an author's own posts as a Word or PDF file: one post, or all of them in one document.

Only the author can export (anyone else gets 404, as for drafts). Rendering is CPU-bound,
so it runs in a worker thread with a time limit, and at most two exports render at once.
The file is built in a spooled temporary file (memory, then disk if large) and streamed out.
"""

import enum
import tempfile
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import IO

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ServiceUnavailableError
from app.models import Post, PostStatus, User
from app.rendering import docx, pdf
from app.rendering.document import ExportDocument, ExportPost
from app.repositories import posts as repo
from app.services.posts import POST_NOT_FOUND

MAX_EXPORT_POSTS = 500
RENDER_TIMEOUT_SECONDS = 25  # below the web proxy's 30 s read timeout
SPOOL_BYTES = 5 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
_render_slots = anyio.CapacityLimiter(2)


class ExportFormat(enum.StrEnum):
    DOCX = "docx"
    PDF = "pdf"


MEDIA_TYPES = {
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ExportFormat.PDF: "application/pdf",
}
_RENDERERS: dict[ExportFormat, Callable[[ExportDocument, IO[bytes]], None]] = {
    ExportFormat.DOCX: docx.render,
    ExportFormat.PDF: pdf.render,
}


class ExportFile:
    """A rendered file and the name it downloads as. `chunks()` closes it when done."""

    def __init__(self, file: IO[bytes], filename: str, media_type: str) -> None:
        self.file, self.filename, self.media_type = file, filename, media_type

    async def chunks(self) -> AsyncIterator[bytes]:
        try:
            self.file.seek(0)
            while chunk := self.file.read(CHUNK_BYTES):
                yield chunk
        finally:
            self.file.close()


def _export_post(post: Post) -> ExportPost:
    return ExportPost(
        title=post.title,
        excerpt=post.excerpt,
        content=post.content,
        tags=[tag.name for tag in post.tags],
        published=post.status == PostStatus.PUBLISHED,
        published_at=post.published_at,
        updated_at=post.updated_at,
    )


async def export_one(session: AsyncSession, user: User, slug: str, fmt: ExportFormat) -> ExportFile:
    post = await repo.get_by_slug(session, slug)
    if post is None or post.author_id != user.id:
        raise NotFoundError(POST_NOT_FOUND)
    document = ExportDocument(
        title=post.title,
        author=user.display_name,
        generated_at=datetime.now(UTC),
        posts=[_export_post(post)],
        collection=False,
    )
    return await _render(document, f"nebula-{post.slug}.{fmt}", fmt)


async def export_all(session: AsyncSession, user: User, fmt: ExportFormat) -> ExportFile:
    posts = await repo.list_for_export(session, user.id, MAX_EXPORT_POSTS)
    if not posts:
        raise NotFoundError("You have no posts to export yet.")
    now = datetime.now(UTC)
    document = ExportDocument(
        title=f"Posts by {user.display_name}",
        author=user.display_name,
        generated_at=now,
        posts=[_export_post(post) for post in posts],
        collection=True,
    )
    return await _render(document, f"nebula-posts-{user.username}-{now:%Y%m%d}.{fmt}", fmt)


async def _render(document: ExportDocument, filename: str, fmt: ExportFormat) -> ExportFile:
    # Not a `with` block: on success the file outlives this function and chunks() closes it.
    file = tempfile.SpooledTemporaryFile(max_size=SPOOL_BYTES)  # noqa: SIM115
    try:
        with anyio.fail_after(RENDER_TIMEOUT_SECONDS):
            await anyio.to_thread.run_sync(
                _RENDERERS[fmt], document, file, limiter=_render_slots, abandon_on_cancel=True
            )
    except TimeoutError:
        file.close()
        raise ServiceUnavailableError(
            "The export took too long. Try exporting fewer posts."
        ) from None
    except BaseException:
        file.close()
        raise
    return ExportFile(file, filename, MEDIA_TYPES[fmt])
