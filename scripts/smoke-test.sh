#!/usr/bin/env bash
# Checks a running Docker stack (`make up`) end to end through the web container, as a browser would.
set -euo pipefail
cd "$(dirname "$0")/.."

web="http://127.0.0.1:${WEB_PORT:-8080}"
fail() { echo "✗ $*" >&2; exit 1; }
ok() { echo "✓ $*"; }

curl -fsS "$web/" | grep -q '<div id="root">' || fail "web app shell not served"
ok "web app shell"

curl -fsS "$web/p/any-post" | grep -q '<div id="root">' || fail "client-side routes don't fall back to the app shell"
ok "client-side routes"

curl -fsS "$web/api/v1/health/ready" | grep -q '"status":"ok"' || fail "API not ready through the proxy"
ok "API ready (database + redis) through the proxy"

headers=$(curl -fsSI "$web/")
grep -qi '^content-security-policy:' <<<"$headers" || fail "web app has no Content-Security-Policy"
grep -qi '^x-content-type-options: nosniff' <<<"$headers" || fail "web app has no nosniff header"
ok "security headers"

! curl -fsS "$web/metrics" | grep -q 'nebula_http' || fail "/metrics is reachable from outside"
docker compose exec -T api python -c \
  "import urllib.request as u; print(u.urlopen('http://127.0.0.1:8000/metrics').read().decode())" \
  | grep -q 'nebula_http_requests_total{' || fail "/metrics not served inside the network"
ok "metrics internal only"

for service in api web; do
  [[ "$(docker compose exec -T "$service" id -u)" != 0 ]] || fail "$service runs as root"
done
ok "containers run as non-root"
