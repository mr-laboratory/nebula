"""Domain errors and their mapping to RFC 9457 Problem Details responses."""

from collections.abc import Mapping
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx

PROBLEM_JSON = "application/problem+json"


class AppError(Exception):
    """Base class for errors that are safe to show to API clients."""

    status_code: int = HTTPStatus.BAD_REQUEST
    default_detail: str = "The request could not be processed."
    headers: Mapping[str, str] | None = None

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class UnauthorizedError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    default_detail = "Authentication is required."
    headers = MappingProxyType({"WWW-Authenticate": "Bearer"})  # read-only, shared


class ForbiddenError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    default_detail = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    default_detail = "The requested resource was not found."


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    default_detail = "The request conflicts with the current state of the resource."


class RateLimitedError(AppError):
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    default_detail = "Too many requests. Please try again later."

    def __init__(self, retry_after: int) -> None:
        super().__init__()
        self.headers = {"Retry-After": str(retry_after)}


def problem_response(
    status: int,
    detail: str,
    instance: str,
    extra: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        "instance": instance,
        "request_id": request_id_ctx.get(),
    }
    if extra:
        body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    err = cast(AppError, exc)
    return problem_response(err.status_code, err.detail, request.url.path, headers=err.headers)


async def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    err = cast(StarletteHTTPException, exc)
    detail = err.detail if isinstance(err.detail, str) else HTTPStatus(err.status_code).phrase
    return problem_response(err.status_code, detail, request.url.path, headers=err.headers)


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Only field location, message and type: never echo submitted input (it may be a password).
    errors = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
        for err in cast(RequestValidationError, exc).errors()
    ]
    return problem_response(
        HTTPStatus.UNPROCESSABLE_CONTENT,
        "The request body or parameters are invalid.",
        request.url.path,
        extra={"errors": errors},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
