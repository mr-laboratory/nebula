"""Schemas shared across resources: pagination parameters, the page envelope, normalisers."""

from pydantic import BaseModel, ConfigDict, Field

MAX_PAGE_SIZE = 100
MAX_OFFSET = 10_000  # deep offsets get slower; clients should narrow with filters instead


def lowercase(value: object) -> object:
    """Trim and lowercase strings (emails, usernames, tags) so comparisons are consistent."""
    return value.strip().lower() if isinstance(value, str) else value


class PageParams(BaseModel):
    # Unknown query parameters are rejected rather than silently ignored.
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(default=0, ge=0, le=MAX_OFFSET)


class Page[T](BaseModel):
    """One page of results, with the total so clients can render pagination."""

    items: list[T]
    total: int
    limit: int
    offset: int
