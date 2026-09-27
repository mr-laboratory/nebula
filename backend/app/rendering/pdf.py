"""PDF export: posts rendered to print-styled HTML, then laid out by WeasyPrint.

WeasyPrint loads nothing from the network or disk except the bundled Geist fonts; every
other URL is refused by the fetcher. It needs the Pango system library, so it's imported
only when a PDF is requested, and its absence is reported as 503 rather than a crash.
"""

import html
from collections.abc import Sequence
from pathlib import Path
from typing import IO, Any

from markdown_it.token import Token

from app.core.errors import ServiceUnavailableError
from app.rendering.document import ExportDocument, ExportPost, parser, safe_href, status_line

FONTS_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
# The only URLs the renderer may load.
FONT_FILES = {path.as_uri(): path for path in FONTS_DIR.glob("*.woff2")}


def _font(family: str, file: str, style: str) -> str:
    # No unicode-range: characters the Latin subset lacks fall back to system fonts
    # (WeasyPrint mis-maps glyphs when one family is split across range-limited files).
    src = (FONTS_DIR / file).as_uri()
    return f"@font-face {{ font-family: '{family}'; font-style: {style}; src: url('{src}'); }}"


STYLESHEET = "\n".join(
    [
        _font("Geist", "geist-latin-wght-normal.woff2", "normal"),
        _font("Geist", "geist-latin-wght-italic.woff2", "italic"),
        _font("Geist Mono", "geist-mono-latin-wght-normal.woff2", "normal"),
        """
@page { size: A4; margin: 22mm 20mm;
  @bottom-center { content: counter(page); font: 9pt Geist, sans-serif; color: #6b7280; } }
@page cover { @bottom-center { content: none; } }
html { font: 10.5pt/1.6 Geist, "DejaVu Sans", sans-serif; color: #111827; }
h1, h2, h3, h4, h5, h6 { line-height: 1.25; margin: 1.4em 0 .5em; break-after: avoid; }
h1 { font-size: 22pt; margin-top: 0; color: #312e81; }
h2 { font-size: 15pt; } h3 { font-size: 12.5pt; } h4, h5, h6 { font-size: 11pt; }
article { break-before: page; }
article:first-of-type { break-before: auto; }
.cover + article { break-before: page; }
.meta { color: #6b7280; font-size: 9pt; margin: 0 0 1em; }
.excerpt { font-style: italic; color: #374151; }
a { color: #4338ca; text-decoration: none; }
code, pre { font-family: "Geist Mono", "DejaVu Sans Mono", monospace; font-size: 9pt; }
code { background: #f3f4f6; padding: 0 .25em; border-radius: 3px; }
pre { background: #f3f4f6; padding: .8em 1em; border-radius: 6px; white-space: pre-wrap;
  break-inside: avoid; }
pre code { background: none; padding: 0; }
blockquote { margin: 1em 0; padding: 0 1em; border-left: 3px solid #c7d2fe; color: #374151; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #d1d5db; padding: .3em .6em; text-align: left; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 2em 0; }
.image { font-style: italic; color: #6b7280; }
.cover { page: cover; }
.cover h1 { font-size: 28pt; margin-top: 30mm; }
.toc { list-style: none; padding: 0; }
.toc li { margin: .35em 0; }
.toc a { color: #111827; }
.toc a::after { content: leader('.') target-counter(attr(href), page); color: #6b7280; }
""",
    ]
)


def _markdown_renderer() -> Any:
    md = parser()
    rules = md.renderer.rules  # type: ignore[attr-defined]  # RendererHTML has them

    def heading_open(tokens: Sequence[Token], idx: int, *_: Any) -> str:
        level = min(int(tokens[idx].tag[1]) + 1, 6)  # the post title is the only <h1>
        return f"<h{level}>"

    def heading_close(tokens: Sequence[Token], idx: int, *_: Any) -> str:
        return f"</h{min(int(tokens[idx].tag[1]) + 1, 6)}>"

    def image(tokens: Sequence[Token], idx: int, *_: Any) -> str:
        alt = "".join(child.content for child in tokens[idx].children or []) or "image"
        return f'<span class="image">[Image: {html.escape(alt)}]</span>'  # never fetched

    def link_open(tokens: Sequence[Token], idx: int, *_: Any) -> str:
        href = safe_href(str(tokens[idx].attrs.get("href", "")))
        return f'<a href="{html.escape(href)}">' if href else "<a>"

    rules["heading_open"] = heading_open
    rules["heading_close"] = heading_close
    rules["image"] = image
    rules["link_open"] = link_open
    return md


def to_html(document: ExportDocument) -> str:
    md = _markdown_renderer()
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        f"<title>{html.escape(document.title)}</title>",
        f"<meta name='author' content='{html.escape(document.author, quote=True)}'>",
        f"<style>{STYLESHEET}</style></head><body>",
    ]
    if document.collection:
        parts.append(_cover(document))
    for index, post in enumerate(document.posts):
        parts.append(_article(md, post, f"post-{index + 1}"))
    parts.append("</body></html>")
    return "".join(parts)


def _cover(document: ExportDocument) -> str:
    entries = "".join(
        f'<li><a href="#post-{index + 1}">{html.escape(post.title)}</a></li>'
        for index, post in enumerate(document.posts)
    )
    return (
        f'<section class="cover"><h1>{html.escape(document.title)}</h1>'
        f'<p class="meta">{html.escape(document.author)} · exported '
        f"{document.generated_at:%d %B %Y}</p>"
        f'<h2>Contents</h2><ol class="toc">{entries}</ol></section>'
    )


def _article(md: Any, post: ExportPost, anchor: str) -> str:
    excerpt = f'<p class="excerpt">{html.escape(post.excerpt)}</p>' if post.excerpt else ""
    return (
        f'<article><h1 id="{anchor}">{html.escape(post.title)}</h1>'
        f'<p class="meta">{html.escape(status_line(post))}</p>{excerpt}'
        f"{md.render(post.content)}</article>"
    )


def render(document: ExportDocument, target: IO[bytes]) -> None:
    try:
        from weasyprint import HTML, URLFetcher  # type: ignore[import-untyped]
        from weasyprint.urls import URLFetcherResponse  # type: ignore[import-untyped]
    except OSError:  # Pango (a system library) isn't installed
        raise ServiceUnavailableError("PDF export isn't available on this server.") from None

    class BundledFontsOnly(URLFetcher):  # type: ignore[misc]
        def fetch(self, url: str, headers: object = None) -> URLFetcherResponse:
            path = FONT_FILES.get(url)
            if path is None:
                raise ValueError("External resources are not loaded in exports.")
            return URLFetcherResponse(url, path.read_bytes(), {"Content-Type": "font/woff2"})

    HTML(string=to_html(document), url_fetcher=BundledFontsOnly()).write_pdf(target)
