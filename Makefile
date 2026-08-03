.PHONY: setup test test-e2e coverage format buildchecks vault clean

# Deliberately mirrors the ai-chat-infrastructure Makefile: same target names,
# same uv invocation style. A developer moving between the two repos should not
# have to learn a second set of commands.

setup:
	uv sync --all-extras

test:
	uv run python -m pytest -v -s --ignore=test/e2e

test-e2e:
	uv run python -m pytest test/e2e -v

coverage:
	uv run python -m pytest --cov=eaf --cov-report=term-missing

format:
	uv run ruff check --fix .
	uv run ruff format .

# The gate. One script, so `make buildchecks` and CI run the identical thing.
buildchecks:
	bash ./build-checks.sh

vault:
	python3 scripts/gen_vault_docs.py

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
