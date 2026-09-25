#!/usr/bin/env bash
# Create a local .env from .env.example with freshly generated secrets.
# Never overwrites an existing .env.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  echo "✓ .env already exists (left unchanged)"
  exit 0
fi

gen() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }

sed -e "s|^JWT_SECRET=.*|JWT_SECRET=$(gen 64)|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(gen 24)|" \
    .env.example > .env
chmod 600 .env
echo "✓ .env created with random secrets (git-ignored, readable only by you)"
