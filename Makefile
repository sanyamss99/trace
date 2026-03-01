.PHONY: install dev test lint check

install:
	uv sync --all-extras

dev:
	uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest -x --tb=short

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

check: lint test
