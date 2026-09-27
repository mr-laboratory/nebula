"""Writing-check endpoint: sends a draft to LanguageTool and returns its suggestions."""

from typing import cast

import httpx
from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, RedisDep, SettingsDep
from app.schemas.writing import WritingCheck, WritingCheckRequest
from app.services import writing

router = APIRouter(prefix="/writing", tags=["writing"])


@router.post("/check", summary="Spelling, grammar and style suggestions for a draft")
async def check_writing(
    body: WritingCheckRequest,
    user: CurrentUser,
    redis: RedisDep,
    settings: SettingsDep,
    request: Request,
) -> WritingCheck:
    """The text goes to LanguageTool's public API and is not stored or logged by Nebula."""
    http = cast(httpx.AsyncClient, request.app.state.http)
    return await writing.check(http, redis, settings, user, body.text, body.language)
