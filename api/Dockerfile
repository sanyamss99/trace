# ---- Builder stage ----
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifest first for layer caching
COPY pyproject.toml ./

# Install production dependencies into a virtual env
RUN uv venv /app/.venv && uv sync --no-dev --no-install-project

# Copy application source and migration files
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini ./

# Install the project itself
RUN uv sync --no-dev

# ---- Runtime stage ----
FROM python:3.11-slim

RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy virtual env and application from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/migrations /app/migrations
COPY --from=builder /app/alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

USER app

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
