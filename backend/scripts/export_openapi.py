"""Print the API's OpenAPI schema as JSON; the frontend generates its TypeScript types from it."""

import json

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    # The schema doesn't depend on secrets or connections, so placeholders keep this runnable
    # anywhere (CI included) without a .env file.
    settings = Settings(
        _env_file=None,
        jwt_secret="openapi-export-placeholder-not-a-secret",  # noqa: S106
        postgres_password="unused",  # noqa: S106
        log_level="WARNING",
    )
    print(json.dumps(create_app(settings).openapi(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
