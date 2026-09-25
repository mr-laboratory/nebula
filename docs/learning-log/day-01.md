# Day 1 — Foundations & secure project setup

## What I built

- Installed the free toolchain: Xcode CLT (git), Homebrew, gh, uv, fnm/Node, Docker CLI + Colima, gitleaks, pre-commit.
- Created the public `nebula` repo with a security-first scaffold.

## Concepts applied

- **Git & GitHub Flow** — `main` is always releasable; work happens on feature branches merged via PR.
- **Secrets hygiene** — `.env` is git-ignored; `.env.example` holds placeholders only.
- **Shift-left security** — pre-commit hooks (gitleaks, private-key detection, noreply-email guard) stop leaks *before* they reach history.
- **Architecture Decision Records** — [ADR 0001](../adr/0001-tech-stack.md) documents why each tool was chosen.

## Lesson learned

Never run destructive git commands (`git stash -u`, `git reset --hard`) in a repo with no commits: there is nothing to restore from. Commit first, then experiment.
