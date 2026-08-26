# Official uv image — Python 3.12 + uv pre-installed, bookworm-slim base.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Apply all available Debian security updates so Trivy finds no fixable CVEs.
# curl is also installed here for the HEALTHCHECK.
# The upgrade step is intentional — without it, Trivy blocks on fixable OS CVEs
# that are patched in Debian's security repo but not in the base image.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Manifests first — Docker caches this layer until pyproject.toml or uv.lock changes.
COPY pyproject.toml uv.lock ./

# uv is already in the base image — no pip install needed.
# --frozen: use exactly what uv.lock says, fail if lock is out of sync.
# --no-dev: exclude test/lint tools from the image.
RUN uv sync --frozen --no-dev

# Source — ordered from least to most frequently changed.
COPY agent/ ./agent/
COPY skills/ ./skills/
COPY scripts/ ./scripts/

# Non-root user.
RUN addgroup --gid 1001 appgroup \
    && adduser --uid 1001 --gid 1001 --no-create-home --disabled-password appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["/app/.venv/bin/python", "-m", "agent"]
