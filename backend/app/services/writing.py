"""'Check my writing': spelling, grammar and style suggestions from LanguageTool.

The draft is sent as annotated text: Markdown syntax, code and link targets are marked as
markup, so LanguageTool checks only the prose but still reports offsets into the original
text. Suggestions touching markup are dropped, so applying one can't break the Markdown.

Draft text is never logged or cached. Offsets count UTF-16 code units, as JavaScript strings
do (LanguageTool runs on the JVM, which counts the same way).
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError, UnprocessableError
from app.core.rate_limit import enforce
from app.models import User
from app.rendering.document import parse
from app.schemas.writing import WritingCheck, WritingIssue, WritingLanguage

logger = logging.getLogger(__name__)

MAX_TEXT_BYTES = 20_000  # LanguageTool's free API accepts about 20 KB per request
MAX_SUGGESTIONS = 5
USER_LIMIT = {"limit": 10, "window": 60}
# Shared by everyone: the free API allows about 20 requests a minute from one address.
GLOBAL_LIMIT = {"limit": 15, "window": 60}
BUSY_RETRY_AFTER = 60
UNAVAILABLE = "The writing check is unavailable right now. Please try again in a minute."

CATEGORIES = {
    "misspelling": "spelling",
    "grammar": "grammar",
    "style": "style",
    "locale-violation": "style",
    "register": "style",
    "typographical": "punctuation",
    "whitespace": "punctuation",
    "duplication": "grammar",
    "inconsistency": "style",
}

_BLOCK_MARKERS = re.compile(
    r"^(?:\s{0,3}(?:#{1,6}\s+|>\s?|[-*+]\s+(?:\[[ xX]\]\s+)?|\d{1,9}[.)]\s+))+"
)
_TABLE_CELL_RULE = re.compile(r":?-{3,}:?")
_INLINE_MARKUP = re.compile(
    r"`+[^`\n]*`+"  # inline code
    r"|!?\["  # link or image opening
    # Link targets and tags stop at the next opener, so "](](](…" or "<<<…" stays linear.
    r"|\](?:\([^()\[\]\s]*(?:\s+\"[^\"\n]*\")?\))?"  # link closing and target
    r"|<[^<>\n]+>"  # autolinks and HTML
    r"|\*\*|__|~~|\*|(?<!\w)_|_(?!\w)"  # emphasis
    r"|\|"  # table cells
)


@dataclass(frozen=True, slots=True)
class _Segment:
    text: str
    markup: bool
    interpret_as: str | None = None


def _is_table_rule(line: str) -> bool:
    """A table's header rule, such as `| --- | :---: |`. Plain string work, no backtracking."""
    stripped = line.strip()
    if "-" not in stripped:
        return False
    cells = stripped.removeprefix("|").removesuffix("|").split("|")
    return all(_TABLE_CELL_RULE.fullmatch(cell.strip()) for cell in cells)


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def annotate(markdown: str) -> list[_Segment]:
    """Split Markdown into prose and markup. Newlines stay prose: they separate sentences."""
    code_lines: set[int] = set()
    for token in parse(markdown):
        if token.type in {"fence", "code_block", "html_block"} and token.map:
            code_lines.update(range(*token.map))

    segments: list[_Segment] = []
    for number, line in enumerate(markdown.split("\n")):
        if number:
            segments.append(_Segment("\n", markup=False))
        if number in code_lines or _is_table_rule(line):
            segments.append(_Segment(line, markup=True))
            continue
        marker = _BLOCK_MARKERS.match(line)
        if marker:
            segments.append(_Segment(marker.group(), markup=True))
            line = line[marker.end() :]
        position = 0
        for match in _INLINE_MARKUP.finditer(line):
            segments.append(_Segment(line[position : match.start()], markup=False))
            code = match.group().startswith("`")
            segments.append(
                _Segment(match.group(), markup=True, interpret_as="code" if code else None)
            )
            position = match.end()
        segments.append(_Segment(line[position:], markup=False))
    return [segment for segment in segments if segment.text]


def _annotation(segments: list[_Segment]) -> str:
    items: list[dict[str, str]] = []
    for segment in segments:
        if not segment.markup:
            items.append({"text": segment.text})
        elif segment.interpret_as:
            items.append({"markup": segment.text, "interpretAs": segment.interpret_as})
        else:
            items.append({"markup": segment.text})
    return json.dumps({"annotation": items})


def _markup_ranges(segments: list[_Segment]) -> list[tuple[int, int]]:
    ranges, offset = [], 0
    for segment in segments:
        length = utf16_len(segment.text)
        if segment.markup:
            ranges.append((offset, offset + length))
        offset += length
    return ranges


async def check(
    http: httpx.AsyncClient, redis: Redis, settings: Settings, user: User, text: str, language: str
) -> WritingCheck:
    if len(text.encode()) > MAX_TEXT_BYTES:
        raise UnprocessableError(
            "This draft is too long to check in one go. Check a shorter part of it."
        )
    await enforce(redis, "writing:user", str(user.id), **USER_LIMIT)
    await enforce(redis, "writing:global", "all", **GLOBAL_LIMIT)

    segments = annotate(text)
    body = await _call(http, settings, {"data": _annotation(segments), "language": language})
    markup = _markup_ranges(segments)
    issues = [
        issue
        for match in body.get("matches", [])
        if (issue := _issue(match)) and not _touches(issue, markup)
    ]
    detected = body.get("language", {}).get("detectedLanguage") or body.get("language", {})
    return WritingCheck(
        language=WritingLanguage(
            code=str(detected.get("code", language)), name=str(detected.get("name", ""))
        ),
        issues=issues,
    )


async def _call(http: httpx.AsyncClient, settings: Settings, form: dict[str, str]) -> Any:
    response: httpx.Response | None = None
    for _attempt in range(2):  # one retry, for transient failures only
        try:
            response = await http.post(settings.languagetool_url, data=form)
        except httpx.HTTPError as exc:
            logger.warning("languagetool request failed", extra={"error": type(exc).__name__})
            continue
        if response.status_code < 500:
            break
        logger.warning("languagetool error", extra={"status": response.status_code})
    if response is None or response.status_code >= 500:
        raise ServiceUnavailableError(UNAVAILABLE)
    if response.status_code == 429:
        raise ServiceUnavailableError(
            "The writing check is busy. Please try again in a minute.",
            retry_after=BUSY_RETRY_AFTER,
        )
    if response.status_code != 200:
        logger.warning("languagetool rejected request", extra={"status": response.status_code})
        raise ServiceUnavailableError(UNAVAILABLE)
    try:
        return response.json()
    except ValueError:
        raise ServiceUnavailableError(UNAVAILABLE) from None


def _issue(match: dict[str, Any]) -> WritingIssue | None:
    try:
        rule = match.get("rule") or {}
        return WritingIssue(
            offset=int(match["offset"]),
            length=int(match["length"]),
            message=str(match.get("message") or match.get("shortMessage") or "Possible issue"),
            category=CATEGORIES.get(str(rule.get("issueType", "")), "other"),
            suggestions=[
                str(r["value"]) for r in (match.get("replacements") or [])[:MAX_SUGGESTIONS]
            ],
        )
    except (KeyError, TypeError, ValueError):
        return None  # skip a malformed match rather than failing the whole check


def _touches(issue: WritingIssue, markup: list[tuple[int, int]]) -> bool:
    end = issue.offset + issue.length
    return any(start < end and issue.offset < stop for start, stop in markup)
