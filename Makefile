.PHONY: install test lint format agent install-hooks

install:
	uv sync --all-extras

install-hooks: ## Install git pre-push hook (runs make test before every push)
	@printf '#!/bin/sh\n# Lint is excluded: this repo currently has pre-existing lint\n# violations (8 as of 2026-07-02) unrelated to any given change.\n# Re-add lint here once that debt is cleaned up.\nmake test\n' > .git/hooks/pre-push
	@chmod +x .git/hooks/pre-push
	@echo "pre-push hook installed"

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

agent:
	set -a && [ -f .env.local ] && . ./.env.local; set +a && \
	uv run civilai-agent run --help
