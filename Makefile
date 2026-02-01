.PHONY: help install lock run report weekly clean lint test coverage

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make lock          - Update lock file"
	@echo "  make run           - Run the daily report generator"
	@echo "  make report        - Alias for 'make run'"
	@echo "  make weekly        - Run the weekly summary report"
	@echo "  make clean         - Clean cache files"
	@echo "  make lint          - Run linter (ruff)"
	@echo "  make test          - Run tests"
	@echo "  make coverage      - Show coverage report"

# Install dependencies
install:
	uv sync

# Update lock file
lock:
	uv lock

# Run the report generator
run:
	uv run python -m src.main

# Alias for run
report: run

# Run weekly report
weekly:
	REPORT_MODE=weekly uv run python -m src.main

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Run linter
lint:
	uv run ruff check src/

# Run tests
test:
	uv run pytest

# Show coverage report
coverage:
	uv run coverage report --show-missing
