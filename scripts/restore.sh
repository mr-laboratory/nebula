#!/usr/bin/env bash
# Replace the local database's contents with a dump made by backup.sh. Asks before overwriting.
set -euo pipefail
cd "$(dirname "$0")/.."

file="${1:-}"
if [[ ! -f "$file" ]]; then
  echo "usage: make restore f=backups/nebula-<timestamp>.dump" >&2
  exit 1
fi

read -r -p "This replaces every table in the local database with $file. Type 'restore' to continue: " answer
[[ "$answer" == "restore" ]] || { echo "Cancelled."; exit 1; }

# --clean --if-exists drops each object before recreating it; one transaction means a failed
# restore leaves the database as it was.
docker compose exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction' \
  < "$file"
echo "✓ restored $file"
