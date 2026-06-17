.PHONY: help install lock run report weekly create-page dry-run clean lint test coverage \
       setup env preflight smoke auth mcp-setup \
       cron-render cron-show cron-install cron-uninstall \
       regression-run regression-score regression regression-compare

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make lock          - Update lock file"
	@echo "  make run           - Run the daily report generator"
	@echo "  make run DATE=YYYY-MM-DD - Run report for a specific date"
	@echo "  make run MODEL=sonnet    - Override Claude model (sonnet/haiku/opus)"
	@echo "  make dry-run       - Run without Slack (stdout only); accepts DATE/MODEL"
	@echo "  make report        - Alias for 'make run'"
	@echo "  make weekly        - Run the weekly summary report"
	@echo "  make create-page   - Create next week's Confluence page"
	@echo "  make create-page DATE=YYYY-MM-DD - Create page for specific week"
	@echo "  make clean         - Clean cache files"
	@echo "  make lint          - Run linter (ruff)"
	@echo "  make test          - Run tests"
	@echo "  make coverage      - Show coverage report"
	@echo ""
	@echo "Setup (new Linux server) - see README 'Installation':"
	@echo "  make setup         - uv sync + scaffold .env + logs/ (no sudo, safe range)"
	@echo "  make env           - Scaffold .env from .env.example (never overwrites)"
	@echo "  make auth          - Interactive: claude auth login (stores creds in ~/.claude)"
	@echo "  make mcp-setup     - Print the 'claude mcp add' command to register MCP servers"
	@echo "  make preflight     - Read-only environment doctor (8 checks)"
	@echo "  make smoke         - Install-complete gate: dry-run E2E (no Slack)"
	@echo ""
	@echo "Cron (Infrastructure-as-Code):"
	@echo "  make cron-render   - Render deploy/report.crontab.tmpl with real paths"
	@echo "  make cron-show     - Show rendered + currently-installed crontab"
	@echo "  make cron-install  - Back up existing crontab, then install rendered one"
	@echo "  make cron-uninstall- Restore the backed-up crontab"
	@echo ""
	@echo "Regression (daily_report prompt accuracy):"
	@echo "  make regression-run [DATE=YYYY-MM-DD]   - Run 23 dry-runs (sonnet x10 + haiku x10 + opus x3)"
	@echo "  make regression-score RUNS_DIR=path     - Score a runs directory with rubric"
	@echo "  make regression [DATE=YYYY-MM-DD]       - Run + score in one shot"
	@echo "  make regression-compare BASE=path NEW=path - Compare two scored runs dirs"

# Install dependencies
install:
	uv sync

# Update lock file
lock:
	uv lock

# Run the report generator
run:
	uv run python -m src.main $(if $(DATE),--date $(DATE)) $(if $(MODEL),--model $(MODEL))

# Alias for run
report: run

# Dry-run: stdout only, no Slack
dry-run:
	DRY_RUN=1 $(MAKE) run $(if $(DATE),DATE=$(DATE)) $(if $(MODEL),MODEL=$(MODEL))

# Run weekly report
weekly:
	REPORT_MODE=weekly uv run python -m src.main $(if $(DATE),--date $(DATE)) $(if $(MODEL),--model $(MODEL))

# Create weekly page
create-page:
	REPORT_MODE=create_page uv run python -m src.main $(if $(DATE),--date $(DATE))

# ─────────────────────────────────────────────────────────────
# Setup (new Linux server). Scope B: deterministic + no sudo.
# OS-level installs (uv/node/claude/mcp-atlassian) are README + preflight-checked.
# ─────────────────────────────────────────────────────────────

# Scaffold .env from template — NEVER overwrite an existing .env (idempotent)
env:
	@if [ -f .env ]; then \
	  echo ".env already exists — left untouched."; \
	else \
	  cp .env.example .env && echo ".env created from .env.example — fill in the values."; \
	fi

# Full safe setup: python deps + .env scaffold + logs/. No sudo, no secret writes.
setup:
	uv sync --locked
	@mkdir -p logs
	@$(MAKE) env
	@echo ""
	@echo "Next (manual — see README 'Installation'):"
	@echo "  1) edit .env"
	@echo "  2) make auth        # claude login"
	@echo "  3) make mcp-setup   # then run the printed command"
	@echo "  4) make preflight   # verify"
	@echo "  5) make smoke       # E2E gate"

# Read-only environment doctor
preflight:
	@bash scripts/preflight.sh

# Install-complete gate: dry-run exercises claude + MCP + Confluence read (no Slack)
smoke:
	DRY_RUN=1 uv run python -m src.main $(if $(DATE),--date $(DATE)) --model $(or $(MODEL),sonnet)

# Interactive Claude auth (stores credentials under ~/.claude; cron needs same user + HOME)
auth:
	claude auth login

# Print the MCP registration command (secrets stay off argv/automation — you run it).
mcp-setup:
	@echo "Register MCP servers at USER scope (headless SDK path needs user scope, not project .mcp.json)."
	@echo "Fill the values, then run:"
	@echo ""
	@echo '  claude mcp add mcp-atlassian -s user \'
	@echo '    -e CONFLUENCE_URL=https://YOUR.atlassian.net/wiki \'
	@echo '    -e CONFLUENCE_USERNAME=you@company.com \'
	@echo '    -e CONFLUENCE_API_TOKEN=*** \'
	@echo '    -e JIRA_URL=https://YOUR.atlassian.net \'
	@echo '    -e JIRA_USERNAME=you@company.com \'
	@echo '    -e JIRA_API_TOKEN=*** \'
	@echo '    -e TOOLSETS=all \'
	@echo "    -- $$HOME/.local/bin/mcp-atlassian"
	@echo ""
	@echo "  # sequential-thinking (used by the report prompt step 4):"
	@echo '  claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking'
	@echo ""
	@echo "Then tighten perms (tokens are stored in plaintext):  chmod 600 ~/.claude.json"
	@echo "Verify:  make preflight"

# ─────────────────────────────────────────────────────────────
# Cron as code. Template is versioned; rendered file + backup are gitignored.
# NOTE: Debian/Ubuntu cron ignores CRON_TZ for firing time — set the server TZ
#   (sudo timedatectl set-timezone Asia/Seoul && sudo systemctl restart cron),
#   or use the UTC times noted in deploy/report.crontab.tmpl.
# ─────────────────────────────────────────────────────────────

cron-render:
	@mkdir -p logs deploy
	@uvbin="$$(dirname "$$(command -v uv)")"; \
	 sed -e "s#__REPO_DIR__#$(CURDIR)#g" -e "s#__UVBIN_DIR__#$$uvbin#g" \
	   deploy/report.crontab.tmpl > deploy/report.crontab
	@echo "Rendered deploy/report.crontab — review it, then 'make cron-install'."

cron-show:
	@echo "-- rendered (deploy/report.crontab) --"
	@cat deploy/report.crontab 2>/dev/null || echo "(none — run 'make cron-render')"
	@echo "-- installed (crontab -l) --"
	@crontab -l 2>/dev/null || echo "(no crontab installed)"

# Overwrites the user crontab (idempotent for this single-app model). Backs up first.
cron-install: cron-render
	@crontab -l > deploy/crontab.backup 2>/dev/null || : > deploy/crontab.backup
	@crontab deploy/report.crontab
	@echo "Installed. Previous crontab backed up to deploy/crontab.backup"
	@echo "Reminder: ensure server TZ is Asia/Seoul (timedatectl) or schedules fire at the wrong hour."

cron-uninstall:
	@if [ -s deploy/crontab.backup ]; then \
	  crontab deploy/crontab.backup && echo "Restored previous crontab from backup."; \
	else \
	  crontab -r 2>/dev/null && echo "Cleared crontab (no backup to restore)." || echo "Nothing to restore or remove."; \
	fi

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

# Regression: run 23 dry-runs (sonnet x10 + haiku x10 + opus x3)
regression-run:
	bash tests/regression/scripts/run_regression.sh $(DATE)

# Regression: score a runs directory
regression-score:
	@if [ -z "$(RUNS_DIR)" ]; then echo "Usage: make regression-score RUNS_DIR=tests/regression/runs/<dir>"; exit 1; fi
	uv run python tests/regression/scripts/score_runs.py $(RUNS_DIR)

# Regression: run + score (auto-detect the most recent runs dir)
regression: regression-run
	@latest=$$(ls -td tests/regression/runs/2* 2>/dev/null | head -1); \
	if [ -n "$$latest" ]; then \
	  echo "Scoring $$latest"; \
	  uv run python tests/regression/scripts/score_runs.py "$$latest"; \
	fi

# Regression: compare baseline vs new runs
regression-compare:
	@if [ -z "$(BASE)" ] || [ -z "$(NEW)" ]; then echo "Usage: make regression-compare BASE=tests/regression/runs/<base> NEW=tests/regression/runs/<new>"; exit 1; fi
	uv run python tests/regression/scripts/compare_runs.py $(BASE) $(NEW)
