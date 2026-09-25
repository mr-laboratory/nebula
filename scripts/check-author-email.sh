#!/usr/bin/env bash
# Pre-commit guard: refuse commits whose author email is not a GitHub noreply address.
# Prevents personal/work emails from ever being published in this public repo's history.
set -euo pipefail
email="$(git config user.email || true)"
if [[ ! "$email" =~ @users\.noreply\.github\.com$ ]]; then
  echo "✗ Commit blocked: author email '$email' is not a GitHub noreply address."
  echo "  Fix: git config user.email \"<id>+<username>@users.noreply.github.com\""
  exit 1
fi
