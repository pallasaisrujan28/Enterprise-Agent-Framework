# Use the official uv image — Python 3.12 + uv pre-installed, bookworm-slim base.
# No need to pip install uv. Fewer CVEs than python:3.11-slim (newer Python + OS).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# curl is not in the base image but needed for the HEALTHCHECK below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy manifests first — Docker caches this layer until pyproject.toml or
# uv.lock changes, so a source-only change skips the dep-install step.
COPY pyproject.toml uv.lock ./

# uv is already in the base image — no pip install needed.
# --frozen: use exactly what uv.lock says, fail if out of sync.
# --no-dev: exclude test/lint tools from the image.
RUN uv sync --frozen --no-dev

# Copy source — ordered from least to most frequently changed.
COPY agent/ ./agent/
COPY agents/ ./agents/
COPY skills/ ./skills/
COPY policies/ ./policies/
COPY guardrails/ ./guardrails/
COPY scripts/ ./scripts/

# Non-root user — principle of least privilege inside the container.
RUN addgroup --gid 1001 appgroup \
    && adduser --uid 1001 --gid 1001 --no-create-home --disabled-password appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

# Run via the venv Python that uv sync created — no uv run overhead at startup.
CMD ["/app/.venv/bin/python", "-m", "agent"]
