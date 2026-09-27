"""JSON log format, request-id correlation and redaction of sensitive fields."""

import json
import logging

from app.core.logging import (
    REDACTED,
    JsonFormatter,
    configure_logging,
    redact,
    request_id_ctx,
    user_id_ctx,
)


def test_redact_masks_sensitive_keys_recursively() -> None:
    data = {
        "username": "nova",
        "password": "hunter2",
        "headers": {"Authorization": "Bearer abc", "Accept": "json"},
        "items": [{"refresh_token": "xyz"}],
    }

    assert redact(data) == {
        "username": "nova",
        "password": REDACTED,
        "headers": {"Authorization": REDACTED, "Accept": "json"},
        "items": [{"refresh_token": REDACTED}],
    }


def test_json_formatter_includes_request_id_and_redacts_extras() -> None:
    record = logging.makeLogRecord(
        {"name": "t", "levelname": "INFO", "msg": "login", "password": "hunter2", "user": "nova"}
    )
    token = request_id_ctx.set("req-123")
    try:
        line = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx.reset(token)

    assert line["msg"] == "login"
    assert line["request_id"] == "req-123"
    assert line["password"] == REDACTED
    assert line["user"] == "nova"


def test_context_is_captured_when_the_record_is_created() -> None:
    configure_logging()
    token = user_id_ctx.set("u-1")
    try:
        record = logging.getLogger("t").makeRecord("t", logging.INFO, "f", 1, "hi", (), None)
    finally:
        user_id_ctx.reset(token)

    # Formatted later (buffered or queued handlers), it still names the user.
    assert json.loads(JsonFormatter().format(record))["user_id"] == "u-1"
