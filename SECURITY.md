# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue. Report privately via this repository's
**Security → Report a vulnerability** tab. You'll get a response as soon as possible.

## Practices in this project

- No secrets in the repo: configuration comes from environment variables; `.env` is git-ignored and only `.env.example` (placeholders) is committed.
- Secret scanning: `gitleaks` runs on every commit (pre-commit) and in CI; GitHub secret scanning + push protection are enabled.
- Commits use a GitHub noreply email (enforced by a pre-commit guard).
- Passwords are hashed with Argon2id; access tokens are short-lived; refresh tokens are rotated and stored hashed.
- API responses use explicit schemas: private fields (email, password hash, tokens) are never returned publicly.
- Dependencies are monitored with Dependabot; code is analysed with CodeQL.
- Seed/demo data is fake only.
