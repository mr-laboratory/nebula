"""Settings validation: env parsing, secret strength and production safeguards."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.conftest import TEST_SECRET


def make(**overrides: object) -> Settings:
    values: dict[str, object] = {"jwt_secret": TEST_SECRET, **overrides}
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_cors_origins_parsed_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://nebula.example")
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:5173", "https://nebula.example"]


def test_short_jwt_secret_rejected() -> None:
    with pytest.raises(ValidationError):
        make(jwt_secret="too-short")


def test_placeholder_secret_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        make(app_env="production", jwt_secret="change-me-generate-a-long-random-value")


def test_debug_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="APP_DEBUG"):
        make(app_env="production", app_debug=True)


def test_secret_is_masked_when_printed() -> None:
    settings = make()

    assert TEST_SECRET not in repr(settings)
