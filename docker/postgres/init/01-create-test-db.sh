#!/usr/bin/env bash
# Runs once on first container start: creates a separate database for the test suite.
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE DATABASE ${POSTGRES_DB}_test OWNER ${POSTGRES_USER};
SQL
