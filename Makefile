.PHONY: install run-ui run-mcp test test-all lint format type-check validate-data

install:
	uv sync

run-ui:
	uv run streamlit run src/anansi/ui/app.py

run-mcp:
	uv run python -m anansi.context.server

test:
	uv run pytest tests/ --collect-only

test-all:
	uv run pytest tests/

lint:
	uv run ruff check src/ tests/ scripts/

format:
	uv run ruff format src/ tests/ scripts/

type-check:
	uv run mypy src/

validate-data:
	uv run python scripts/validate_context_packs.py
