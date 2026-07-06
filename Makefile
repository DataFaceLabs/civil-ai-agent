.PHONY: install test lint typecheck format agent install-hooks gauntlet

install:
	uv sync --all-extras

install-hooks: ## Install git pre-push hook (runs make gauntlet before every push)
	@printf '#!/bin/sh\nmake gauntlet\n' > .git/hooks/pre-push
	@chmod +x .git/hooks/pre-push
	@echo "pre-push hook installed"

# CI-parity quality gate (same name and shape as civil-ai-data's `make gauntlet`).
# Run before every PR/push. Keep it green — never re-exclude a step to "fix later".
gauntlet: lint typecheck test

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run mypy

format:
	uv run ruff check --fix .
	uv run ruff format .

agent:
	set -a && [ -f .env.local ] && . ./.env.local; set +a && \
	uv run civilai-agent run --help
