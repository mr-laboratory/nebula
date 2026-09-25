"""JSON log format, request-id correlation and redaction of sensitive fields."""

import json
import logging

from app.core.logging import REDACTED, JsonFormatter, redact, request_id_ctx


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
