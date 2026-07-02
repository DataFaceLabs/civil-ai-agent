.PHONY: install test lint format agent

install:
	uv sync --all-extras

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
