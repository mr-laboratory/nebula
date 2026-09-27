# syntax=docker/dockerfile:1
# Nebula API image: dependencies are installed with uv in a build stage; the runtime stage
# gets only the virtualenv and the app code, and runs as an unprivileged user.

ARG PYTHON_VERSION=3.13

FROM ghcr.io/astral-sh/uv:0.12.19 AS uv

# ─── Build: resolve and install locked, production-only dependencies ─────────────
FROM python:${PYTHON_VERSION}-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

# ─── Runtime: no uv, no compilers, no dev tools ─────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime
RUN groupadd --system --gid 10001 nebula \
 && useradd --system --uid 10001 --gid nebula --no-create-home --shell /usr/sbin/nologin nebula
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY app ./app
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production
USER nebula
EXPOSE 8000
# Liveness: the process answers. Compose overrides this with readiness to order start-up.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=2)"]
# --proxy-headers: the client IP (used by rate limits) comes from X-Forwarded-For, which the
# web container overwrites. Safe only because the API port is never published.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "*"]
