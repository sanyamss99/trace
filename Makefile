.PHONY: install dev test lint format check publish-sdk

install:
	uv sync --all-packages

dev:
	cd api && uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd api && uv run pytest -x --tb=short
	cd sdk && uv run pytest -x --tb=short

lint:
	uv run ruff check sdk/ api/
	uv run ruff format --check sdk/ api/

format:
	uv run ruff check --fix sdk/ api/
	uv run ruff format sdk/ api/

check: lint test

publish-sdk:
	uv build --package usetrace && uv publish dist/usetrace-*
