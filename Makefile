.PHONY: help install lock run report clean lint test coverage cron-install cron-uninstall cron-status cron-logs

# Project configuration
PROJECT_DIR := $(shell pwd)
UV_PATH := $(shell which uv)
SHELL_PATH := $(shell echo $$PATH)
LOG_DIR := $(PROJECT_DIR)/logs
CRON_SCHEDULE := 0 12 * * 1-5
CRON_MARKER := \# report-generator-cron

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make lock          - Update lock file"
	@echo "  make run           - Run the daily report generator"
	@echo "  make report        - Alias for 'make run'"
	@echo "  make clean         - Clean cache files"
	@echo "  make lint          - Run linter (ruff)"
	@echo "  make test          - Run tests"
	@echo "  make coverage      - Show coverage report"
	@echo ""
	@echo "Cron commands:"
	@echo "  make cron-install  - Register cron job (Mon-Fri 12:00 PM)"
	@echo "  make cron-uninstall- Remove cron job"
	@echo "  make cron-status   - Show registered cron jobs"
	@echo "  make cron-logs     - Tail cron logs"

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

# ========================================
# Cron Job Management
# ========================================

# Create logs directory
$(LOG_DIR):
	@mkdir -p $(LOG_DIR)

# Install cron job
cron-install: $(LOG_DIR)
	@echo "Installing cron job..."
	@(crontab -l 2>/dev/null | grep -v "$(CRON_MARKER)"; \
	  echo "$(CRON_SCHEDULE) export PATH=$(SHELL_PATH) && cd $(PROJECT_DIR) && $(UV_PATH) run python -m src.main >> $(LOG_DIR)/cron.log 2>&1 $(CRON_MARKER)") | crontab -
	@echo "✓ Cron job installed: $(CRON_SCHEDULE) (Mon-Fri 12:00 PM)"
	@echo "  Log file: $(LOG_DIR)/cron.log"

# Uninstall cron job
cron-uninstall:
	@echo "Removing cron job..."
	@crontab -l 2>/dev/null | grep -v "$(CRON_MARKER)" | crontab - || true
	@echo "✓ Cron job removed"

# Show cron status
cron-status:
	@echo "Current cron jobs for report-generator:"
	@crontab -l 2>/dev/null | grep "$(CRON_MARKER)" || echo "  (none registered)"
	@echo ""
	@echo "All cron jobs:"
	@crontab -l 2>/dev/null || echo "  (no crontab)"

# Tail cron logs
cron-logs:
	@if [ -f "$(LOG_DIR)/cron.log" ]; then \
		tail -f $(LOG_DIR)/cron.log; \
	else \
		echo "Log file not found: $(LOG_DIR)/cron.log"; \
		echo "The log will be created after the first cron execution."; \
	fi
