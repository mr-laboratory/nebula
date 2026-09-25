"""Auth endpoints: register, login, refresh (rotating cookie) and logout."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response, status

from app.api.deps import RedisDep, SessionDep, SettingsDep
from app.core.config import Settings
from app.core.errors import UnauthorizedError
from app.core.rate_limit import enforce
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserMe
from app.services import auth, users
from app.services.auth import SESSION_EXPIRED, IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "nebula_refresh"
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE, include_in_schema=False)]


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _cookie_path(settings: Settings) -> str:
    return f"{settings.api_prefix}/auth"  # the browser sends the cookie only to auth routes


def _token_response(response: Response, tokens: IssuedTokens, settings: Settings) -> TokenResponse:
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        path=_cookie_path(settings),
        httponly=True,  # JavaScript can't read it, so XSS can't steal it
        secure=True,  # HTTPS only (browsers treat http://localhost as secure)
        samesite="strict",  # never sent on cross-site requests, which blocks CSRF
    )
    return TokenResponse(
        access_token=tokens.access_token, expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Create an account")
async def register(
    body: RegisterRequest, request: Request, session: SessionDep, redis: RedisDep
) -> UserMe:
    await enforce(redis, "register:ip", _client_ip(request), limit=10, window=3600)
    user = await auth.register(session, body)
    return await users.get_me(session, user.id)


@router.post("/login", summary="Sign in and receive an access token")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> TokenResponse:
    """Returns a short-lived access token and sets a rotating, httpOnly refresh cookie."""
    await enforce(redis, "login:ip", _client_ip(request), limit=5, window=60)
    await enforce(redis, "login:email", body.email, limit=10, window=900)
    user = await auth.authenticate(session, body.email, body.password.get_secret_value())
    tokens = await auth.issue_tokens(session, user.id, settings)
    return _token_response(response, tokens, settings)


@router.post("/refresh", summary="Exchange the refresh cookie for a new access token")
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    refresh_token: RefreshCookie = None,
) -> TokenResponse:
    await enforce(redis, "refresh:ip", _client_ip(request), limit=30, window=60)
    if not refresh_token:
        raise UnauthorizedError(SESSION_EXPIRED)
    tokens = await auth.rotate(session, refresh_token, settings)
    return _token_response(response, tokens, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
async def logout(
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    refresh_token: RefreshCookie = None,
) -> None:
    """Revokes the session's refresh tokens. Works even if the access token has expired."""
    if refresh_token:
        await auth.logout(session, refresh_token)
    response.delete_cookie(
        REFRESH_COOKIE, path=_cookie_path(settings), httponly=True, secure=True, samesite="strict"
    )
