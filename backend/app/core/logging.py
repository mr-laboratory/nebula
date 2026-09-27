"""JSON logging with request-id and user-id correlation and redaction of sensitive fields."""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
# Set once the request's access token is verified; an opaque id, never a username or email.
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)

REDACTED = "[REDACTED]"
SENSITIVE_KEY = re.compile(r"pass(word)?|secret|token|authorization|cookie|api[_-]?key", re.I)

_CONTEXT = {"request_id": request_id_ctx, "user_id": user_id_ctx}
_CONTEXT_ATTR = "_nebula_context"  # private, so it can't clash with a key passed in `extra=`

# Attributes every LogRecord has; anything else was passed via `extra=`.
_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "taskName",
    _CONTEXT_ATTR,
}
_base_record_factory = logging.getLogRecordFactory()


def _record_with_context(*args: Any, **kwargs: Any) -> logging.LogRecord:
    """Stamp the request context on each record when it's created, not when it's formatted,
    so handlers that format later (buffered, queued, test capture) still see it."""
    record = _base_record_factory(*args, **kwargs)
    setattr(record, _CONTEXT_ATTR, {name: var.get() for name, var in _CONTEXT.items()})
    return record


def redact(value: Any) -> Any:
    """Recursively replace values whose key looks sensitive."""
    if isinstance(value, dict):
        return {
            k: REDACTED if SENSITIVE_KEY.search(str(k)) else redact(v) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        stamped = getattr(record, _CONTEXT_ATTR, {})
        for name, var in _CONTEXT.items():
            if value := stamped.get(name) or var.get():
                payload[name] = value
        extras = {k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS}
        payload.update(redact(extras))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    logging.setLogRecordFactory(_record_with_context)

    # Route uvicorn's own loggers through our formatter; we emit our own access log.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
