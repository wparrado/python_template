# ── Stage 1: dependency installer ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests first (layer caching — uv.lock pins exact versions)
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install runtime dependencies only (no dev tools)
RUN uv sync --no-dev --no-editable

# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the installed virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src

# Make the venv available
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["granian", "--interface", "asgi", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
