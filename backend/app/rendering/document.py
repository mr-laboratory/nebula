"""What an export contains, and the Markdown parser both renderers share.

Raw HTML in posts is never interpreted (`html: False` turns it into plain text), and images
are never fetched: renderers show their alt text instead, so exporting can't be made to
request internal URLs (SSRF) or embed someone else's content.
"""

from dataclasses import dataclass
from datetime import datetime

from markdown_it import MarkdownIt
from markdown_it.token import Token

SAFE_LINK_SCHEMES = ("http://", "https://", "mailto:")


@dataclass(frozen=True, slots=True)
class ExportPost:
    title: str
    excerpt: str | None
    content: str
    tags: list[str]
    published: bool
    published_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ExportDocument:
    title: str
    author: str  # the exporting author's display name
    generated_at: datetime
    posts: list[ExportPost]
    collection: bool  # export-all: adds a cover page and a contents list


def parser() -> MarkdownIt:
    # Same Markdown features as the web app (GitHub-style tables and strikethrough).
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


def parse(markdown: str) -> list[Token]:
    return parser().parse(markdown)


def safe_href(href: str) -> str | None:
    """Only web and mail links stay clickable; anything else is exported as plain text."""
    return href if href.lower().startswith(SAFE_LINK_SCHEMES) else None


def status_line(post: ExportPost) -> str:
    if post.published and post.published_at:
        state = f"Published {post.published_at:%d %B %Y}"
    else:
        state = f"Draft, last edited {post.updated_at:%d %B %Y}"
    return f"{state} · {', '.join(post.tags)}" if post.tags else state
