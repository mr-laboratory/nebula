"""Migrations: models and migrations agree, and every migration can be rolled back."""

from alembic import command

from app.core.config import Settings
from tests.conftest import alembic_config


def test_models_match_migrations(migrated_db: None, settings: Settings) -> None:
    # Fails if a model changed without a matching migration.
    command.check(alembic_config(settings))


def test_downgrade_and_upgrade_round_trip(migrated_db: None, settings: Settings) -> None:
    config = alembic_config(settings)

    command.downgrade(config, "base")
    command.upgrade(config, "head")
