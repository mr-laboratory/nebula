"""'Check my writing': Markdown masking, LanguageTool responses, failures and limits."""

import json
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.services.writing import annotate
from tests.conftest import signed_in

CHECK = "/api/v1/writing/check"
Handler = Callable[[httpx.Request], httpx.Response]


def languagetool_reply(*matches: dict[str, Any]) -> dict[str, Any]:
    return {
        "language": {"detectedLanguage": {"name": "English (US)", "code": "en-US"}},
        "matches": list(matches),
    }


def match(offset: int, length: int, issue_type: str, *values: str) -> dict[str, Any]:
    return {
        "offset": offset,
        "length": length,
        "message": "Possible problem",
        "replacements": [{"value": value} for value in values],
        "rule": {"issueType": issue_type},
    }


async def use_languagetool(app: FastAPI, handler: Handler) -> list[httpx.Request]:
    """Swap the outbound client for a fake LanguageTool; returns the requests it receives."""
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    await app.state.http.aclose()
    app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(record))
    return seen


def sent_annotation(request: httpx.Request) -> list[dict[str, str]]:
    form = parse_qs(request.content.decode())
    items: list[dict[str, str]] = json.loads(form["data"][0])["annotation"]
    return items


# ─── Masking ──────────────────────────────────────────────


def test_markdown_syntax_is_markup_and_prose_is_text() -> None:
    text = "## Title\n\nSee [the docs](https://x.io) and `code`.\n\n```\nnot prose\n```"

    segments = annotate(text)

    assert "".join(segment.text for segment in segments) == text  # offsets line up
    prose = "".join(segment.text for segment in segments if not segment.markup)
    assert "Title" in prose and "the docs" in prose
    assert "##" not in prose and "https://x.io" not in prose
    assert "code" not in prose and "not prose" not in prose


# ─── Checking ─────────────────────────────────────────────


async def test_issues_come_back_with_offsets_into_the_markdown(
    app: FastAPI, client: AsyncClient
) -> None:
    ada = await signed_in(client)
    text = "## This are fine\n\nTeh [lnik](https://example.com)."
    seen = await use_languagetool(
        app,
        lambda _: httpx.Response(
            200,
            json=languagetool_reply(
                match(8, 3, "grammar", "is"),
                match(18, 3, "misspelling", "The", "Ten", "Tea", "Tee", "Toe", "Tech"),
                match(0, 7, "typographical"),  # overlaps the "## " markup: dropped
            ),
        ),
    )

    response = await client.post(CHECK, json={"text": text}, headers=ada)
    body = response.json()

    assert response.status_code == 200
    assert body["language"] == {"code": "en-US", "name": "English (US)"}
    assert [(i["offset"], i["length"], i["category"]) for i in body["issues"]] == [
        (8, 3, "grammar"),
        (18, 3, "spelling"),
    ]
    assert text[18:21] == "Teh"
    assert body["issues"][1]["suggestions"] == ["The", "Ten", "Tea", "Tee", "Toe"]
    annotation = sent_annotation(seen[0])
    assert {"markup": "## "} in annotation
    assert {"markup": "](https://example.com)"} in annotation
    assert parse_qs(seen[0].content.decode())["language"] == ["auto"]


async def test_languagetool_busy_becomes_503_with_retry_after(
    app: FastAPI, client: AsyncClient
) -> None:
    ada = await signed_in(client)
    await use_languagetool(app, lambda _: httpx.Response(429))

    response = await client.post(CHECK, json={"text": "Hello"}, headers=ada)

    assert response.status_code == 503
    assert response.headers["retry-after"] == "60"


async def test_transient_failure_is_retried_once(app: FastAPI, client: AsyncClient) -> None:
    ada = await signed_in(client)
    replies = iter([httpx.Response(502), httpx.Response(200, json=languagetool_reply())])
    seen = await use_languagetool(app, lambda _: next(replies))

    response = await client.post(CHECK, json={"text": "Hello"}, headers=ada)

    assert response.status_code == 200 and len(seen) == 2


async def test_languagetool_down_becomes_503(app: FastAPI, client: AsyncClient) -> None:
    ada = await signed_in(client)

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    seen = await use_languagetool(app, unreachable)

    response = await client.post(CHECK, json={"text": "Hello"}, headers=ada)

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]
    assert len(seen) == 2


async def test_text_over_the_byte_limit_is_rejected(app: FastAPI, client: AsyncClient) -> None:
    ada = await signed_in(client)
    seen = await use_languagetool(app, lambda _: httpx.Response(200, json=languagetool_reply()))

    response = await client.post(CHECK, json={"text": "é" * 15_000}, headers=ada)  # 30 KB

    assert response.status_code == 422 and not seen


async def test_writing_check_is_rate_limited_per_user(app: FastAPI, client: AsyncClient) -> None:
    ada = await signed_in(client)
    await use_languagetool(app, lambda _: httpx.Response(200, json=languagetool_reply()))

    statuses = [
        (await client.post(CHECK, json={"text": "Hi"}, headers=ada)).status_code for _ in range(11)
    ]

    assert statuses == [200] * 10 + [429]


async def test_writing_check_requires_sign_in(client: AsyncClient) -> None:
    response = await client.post(CHECK, json={"text": "Hello"})

    assert response.status_code == 401


@pytest.mark.parametrize("enabled", [True, False])
async def test_writing_check_can_be_switched_off(settings: Settings, enabled: bool) -> None:
    app = create_app(settings.model_copy(update={"writing_check_enabled": enabled}))
    try:
        assert (CHECK in app.openapi()["paths"]) is enabled
    finally:
        await app.state.http.aclose()
        await app.state.redis.aclose()
        await app.state.db.dispose()
