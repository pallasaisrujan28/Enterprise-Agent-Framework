FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy manifest and lock file first so Docker caches the dep-install layer.
# uv sync --frozen installs exactly what uv.lock specifies — reproducible builds.
# If uv.lock is out of sync with pyproject.toml, the build fails loudly here.
# To regenerate: run `uv lock` locally and commit the updated uv.lock.
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

# Copy source — ordered from least to most frequently changed.
COPY agent/ ./agent/
COPY agents/ ./agents/
COPY skills/ ./skills/
COPY policies/ ./policies/
COPY guardrails/ ./guardrails/
COPY scripts/ ./scripts/

RUN addgroup --gid 1001 appgroup \
    && adduser --uid 1001 --gid 1001 --no-create-home --disabled-password appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python", "-m", "agent"]
