#!/usr/bin/env bash
# Dump the local database to backups/nebula-<UTC timestamp>.dump (pg_dump custom format).
# Backups contain personal data (emails, password hashes), so the folder is git-ignored and
# the files are readable only by you.
set -euo pipefail
cd "$(dirname "$0")/.."

umask 077
mkdir -p backups
file="backups/nebula-$(date -u +%Y%m%dT%H%M%SZ).dump"

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > "$file.partial"
mv "$file.partial" "$file"  # a half-written dump never looks like a finished one
echo "✓ $file ($(du -h "$file" | cut -f1))"
