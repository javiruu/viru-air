# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS builder

# Pin uv independently from the application dependency lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Install only locked production dependencies first for layer reuse.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# The project is copied as source because the runtime needs Alembic and
# package data/fixtures as well as the importable application modules.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_FILE=/tmp/viru.log \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app

COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --from=builder --chown=app:app /app/app /app/app
COPY --from=builder --chown=app:app /app/alembic /app/alembic
COPY --from=builder --chown=app:app /app/alembic.ini /app/alembic.ini

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
