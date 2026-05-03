# syntax=docker/dockerfile:1.7

# ─── Builder: install deps with uv (fast, deterministic via uv.lock) ───
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Layer 1: dependencies (cached unless pyproject.toml or uv.lock changes).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Layer 2: project source + final install.
COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ─── Runtime: small slim image, non-root, /data volume mount target ───
FROM python:3.12-slim-bookworm

# Non-root user. Fly's volume mount will be chowned to this uid below.
RUN useradd --create-home --uid 1000 pathwise

WORKDIR /app
COPY --from=builder --chown=pathwise:pathwise /app /app

# Persistent volume mount target. Fly mounts the volume here per fly.toml.
ENV PATHWISE_DATA_DIR=/data \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data && chown pathwise:pathwise /data

USER pathwise
EXPOSE 8000

# Single uvicorn worker on purpose — multiple workers would race on the
# fcntl-locked flat-file store.
CMD ["uvicorn", "pathwise.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
