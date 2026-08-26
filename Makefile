SHELL := /bin/bash
.PHONY: setup test test-e2e coverage format check buildchecks install-hooks clean

# ── Local setup ───────────────────────────────────────────────────────────────

setup:
	uv sync --all-extras

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
