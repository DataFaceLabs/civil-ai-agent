.PHONY: install test lint format agent install-hooks gauntlet

install:
	uv sync --all-extras

install-hooks: ## Install git pre-push hook (runs make gauntlet before every push)
	@printf '#!/bin/sh\nmake gauntlet\n' > .git/hooks/pre-push
	@chmod +x .git/hooks/pre-push
	@echo "pre-push hook installed"

# Lint is excluded: this repo currently has pre-existing lint violations (8 as of
# 2026-07-02) unrelated to any given change. Re-add here once that debt is cleaned up.
# Same command name as civil-ai-data's `make gauntlet` -- run this before every PR.
gauntlet: test

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
