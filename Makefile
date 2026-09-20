SHELL := /bin/bash
.PHONY: setup test test-e2e coverage format check buildchecks install-hooks clean \
        local-up local-down local-check local-logs local-reset dashboard

# ── Local setup ───────────────────────────────────────────────────────────────

setup:
	uv sync --all-extras

# ── The local stack ───────────────────────────────────────────────────────────
# The same backing services the cloud deployment uses, on one machine. ADR-019
# makes this the gate: nothing is deployed to EKS until it works here.
#
# Bedrock is NOT in the stack — model calls go to the real service in every
# environment (ADR-011), so this needs AWS credentials and it does bill.
#
#   cp .env.local.example .env.local   then   set -a; . ./.env.local; set +a

local-up:
	docker compose up -d
	@echo ""
	@echo "Qdrant   http://localhost:6333/dashboard"
	@echo "SearXNG  http://localhost:8088"
	@echo "MinIO    http://localhost:9001   (eaflocal / eaflocal-dev-password)"
	@echo ""
	@echo "Now: make local-check"

local-down:
	docker compose down

# Verifies each service ANSWERS the call the application makes — `docker compose
# ps` only proves a container is running, which is not the same thing. SearXNG in
# particular runs happily while refusing JSON.
local-check:
	uv run python scripts/local_check.py

local-logs:
	docker compose logs -f --tail=50

# Destroys the named volumes too, so Qdrant collections and the MinIO bucket go.
local-reset:
	docker compose down -v
	@echo "Volumes removed. 'make local-up' starts from empty."

dashboard:
	uv run python -m agent.cli dashboard

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	uv run python -m pytest -v -s --ignore=test/e2e

test-e2e:
	uv run python -m pytest test/e2e -v

coverage:
	uv run python -m pytest --cov=agent --cov-report=term-missing

# ── Code quality ──────────────────────────────────────────────────────────────

# Auto-fix: ruff lint + format in place. Run before committing.
format:
	uv run ruff check --fix .
	uv run ruff format .

# Fast check: lint + format only (~3s). Used by pre-push hook.
# Run 'make format' to auto-fix, then 'make check' to verify.
check:
	uv run ruff check .
	uv run ruff format --check .

# Full gate — same as CI. One target, identical locally and in CI.
# Runs: pip-audit → ruff → mypy → pytest (with coverage).
buildchecks:
	bash ./build-checks.sh

# ── Git hooks ─────────────────────────────────────────────────────────────────

install-hooks:
	git config core.hooksPath .githooks
	@echo "Pre-push hook installed — 'make check' runs before every push."

# ── Housekeeping ──────────────────────────────────────────────────────────────

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
