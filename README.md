# Weekly Report Generator

This script automatically generates a daily/weekly report by summarizing content from Confluence pages and associated JIRA tickets, and then sends the report to a specified Slack channel.

## Description

The script supports three modes: **daily** (default), **weekly**, and **create_page**.

### Daily Mode
1.  **Calculates Date Range:** Automatically determines this week's date range (Monday to Friday).
2.  **Generates Reports:** Uses the `/daily_report` command via the Claude CLI to:
    *   Search and read the Confluence page by space key and calculated page title.
    *   Extract team members' work content for today.
    *   Generate a C-Level formatted report.
3.  **Sends to Slack:** Posts the generated report to a configured Slack channel.

### Weekly Mode
1.  **Calculates Date Range:** Determines the full week range (Monday to Friday).
2.  **Generates Summary:** Uses the `/weekly_report` command via CLI tool to:
    *   Read all daily pages from the week.
    *   Summarize the week's work into a consolidated report.
3.  **Sends to Slack:** Posts the weekly summary with title format `[{prefix}][{YY.MM.DD}_Weekly]`.

## Prerequisites

Install these on the server (see **Installation (Linux server)** below for the full flow):

*   Python 3.12+
*   [uv](https://github.com/astral-sh/uv)
*   Node.js + npm (required by the Claude CLI and the `sequential-thinking` MCP server)
*   [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) — **authenticated** (`claude auth login`)
*   `mcp-atlassian` MCP server (`uv tool install mcp-atlassian`), **registered with the Claude CLI**
*   The Python libraries in `pyproject.toml` (installed via `make setup`)

> ⚠️ The report's Confluence/JIRA **reads** (daily/weekly) go through the `mcp-atlassian` MCP server configured in the Claude CLI (`~/.claude.json`), **not** via `.env`. This is the most commonly missed step — `make preflight` checks for it. (The `CONFLUENCE_*` keys in `.env` are only for the `create_page` mode's REST calls.)

## Installation (Linux server)

Deterministic steps are automated in the `Makefile`; secret/interactive steps are manual. Target: a fresh Debian/Ubuntu (apt) server.

**1. System dependencies** (one-time; may need sudo — intentionally NOT done by `make`):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh            # uv
sudo apt-get update && sudo apt-get install -y nodejs npm  # Node.js
npm install -g @anthropic-ai/claude-code                   # Claude CLI
uv tool install mcp-atlassian                              # Atlassian MCP server
```

**2. Get the code + scaffold** (no sudo):
```bash
git clone <repo> && cd report
make setup        # uv sync --locked + create .env (from .env.example) + create logs/
```

**3. Fill secrets** — edit `.env` (Slack token/channels, `CONFLUENCE_SPACE_KEY`, and the `create_page` Confluence REST creds). Each key is documented in **Setup** below.

**4. Authenticate the Claude CLI** (interactive; stores creds under `~/.claude`):
```bash
make auth         # = claude auth login    (alternative for CI: claude setup-token)
```

**5. Register MCP servers** at user scope (you enter the tokens; nothing is committed):
```bash
make mcp-setup    # prints the exact `claude mcp add ...` command — fill the values and run it
chmod 600 ~/.claude.json   # tokens are stored in plaintext
```

**6. Verify:**
```bash
make preflight    # 8-point doctor: deps, .env, claude auth, MCP registration
make smoke        # E2E gate: dry-run exercising Claude + MCP + Confluence read (no Slack)
```
If `make smoke` prints a report to stdout, the install is complete.

**7. Timezone** (schedules below are Asia/Seoul; Debian/Ubuntu cron uses the **system** timezone — it ignores `CRON_TZ` for firing time):
```bash
sudo timedatectl set-timezone Asia/Seoul && sudo systemctl restart cron
```

Then schedule the jobs — see **Scheduling (cron)** below.

## Setup

Environment variables live in `.env` (created by `make setup`; never committed). `.env.example` is the template and `src/infrastructure/config.py` is the authoritative key list.

```
# Slack Configuration
SLACK_TOKEN="YOUR_SLACK_BOT_TOKEN"
SLACK_CHANNEL="YOUR_SLACK_CHANNEL_ID"
SLACK_CHANNEL_WEEKLY="YOUR_WEEKLY_SLACK_CHANNEL_ID"  # Optional, separate channel for weekly reports
SLACK_CHANNEL_CREATE_PAGE="YOUR_CREATE_PAGE_SLACK_CHANNEL_ID"  # Optional, separate channel for create_page mode notifications

# Confluence Configuration
CONFLUENCE_SPACE_KEY="MAI"

# Report Configuration
REPORT_TEAM_NAME="Backend Team"  # Optional, used in report header
REPORT_TEAM_PREFIX="BE"  # Optional, team prefix for Slack message title (e.g., [BE][26.01.27_Daily])
REPORT_MENTION_USERS="@홍길동 @김철수"  # Optional, users to mention on delay/hold items

# CLI Configuration
CLI_TYPE="claude"  # Optional, "claude" (default, only supported value)
CLI_MODEL="sonnet"  # Optional, Claude model alias (sonnet/haiku/opus). Default: sonnet
DRY_RUN="0"  # Optional, "1" or "true" to print report to stdout without Slack

# Report Mode
REPORT_MODE="daily"  # Optional, "daily" (default), "weekly", or "create_page"

# Confluence API Configuration (for create_page mode)
CONFLUENCE_URL="https://your-instance.atlassian.net"
CONFLUENCE_USER="your-email@company.com"
CONFLUENCE_TOKEN="your-api-token"
PARENT_PAGE_ID="your-parent-page-id"
```

*   `SLACK_TOKEN`: Your Slack bot token with `chat:write` permission.
*   `SLACK_CHANNEL`: The ID of the Slack channel where daily reports will be sent.
*   `SLACK_CHANNEL_WEEKLY`: (Optional) Channel for weekly reports. If not set, weekly reports are skipped.
*   `SLACK_CHANNEL_CREATE_PAGE`: (Optional) Channel for `create_page` notifications. If not set, notifications are skipped — page creation continues normally.
*   `CONFLUENCE_SPACE_KEY`: The Confluence space key where the daily pages live. **Required** (the app exits with code 1 if unset).
*   `REPORT_TEAM_NAME` / `REPORT_TEAM_PREFIX` / `REPORT_MENTION_USERS`: (Optional) Report header, Slack-title prefix, and delay/hold mentions.
*   `CLI_TYPE`: (Optional) `claude` (default, only supported value).
*   `CLI_MODEL`: (Optional) `sonnet` (default & **recommended**), `haiku`, `opus`. CLI flag `--model` takes precedence. See [Recommended Model](#recommended-model).
*   `DRY_RUN`: (Optional) Truthy (`1`, `true`) prints to stdout instead of Slack. CLI flag `--dry-run` takes precedence.
*   `REPORT_MODE`: (Optional) `daily` (default), `weekly`, or `create_page`.
*   `CONFLUENCE_URL` / `CONFLUENCE_USER` / `CONFLUENCE_TOKEN` / `PARENT_PAGE_ID`: (Required for `create_page` mode) Instance URL, user email, API token, and parent page ID. `CONFLUENCE_URL` may omit the `/wiki` suffix — the adapter appends it. (This is the app's REST config; the `mcp-atlassian` server has its own `CONFLUENCE_URL`, which **does** need `/wiki`.)

The report generation logic itself is defined in `.claude/commands/daily_report.md` and `.claude/commands/weekly_report.md`, executed by the Claude CLI.

## Recommended Model

Based on a 23-run regression test (`tests/regression/`) against ground truth on 2026-05-15, the recommended model for production is **`sonnet`**.

| Model | Avg Score (15 pts) | Stdev | Lowest | Highest | Infrastructure Failures | Note |
|-------|--------------------|-------|--------|---------|-----------------------|------|
| **Sonnet** | **15.00** 🏆 | 0.00 | 15.0 | 15.0 | 0/10 | **Recommended for production** |
| Haiku | 12.14 | 1.44 | 9.67 | 15.0 | 0/10 | Lower cost, variable quality |
| Opus | 10.67 (15.0†) | 7.51 | 2.0 | 15.0 | 1/3 | †Excluding 1 infra failure. Higher cost, occasional CLI failure |

**Why Sonnet:**
- Perfect score with zero variance across 10 runs (deterministic for our prompt)
- ~1/5 cost of Opus
- No infrastructure failures observed
- Faster than Opus (~2min vs ~4min per run)

Set `CLI_MODEL=sonnet` in `.env` (already the default fallback if unset).

## Usage

To run the script, execute the following command from the root of the project:

```bash
# Run daily report (default - today's date)
uv run python -m src.main
# or: make run

# Run report for a specific date
uv run python -m src.main --date 2026-04-06
# or: make run DATE=2026-04-06

# Choose Claude model (sonnet/haiku/opus). CLI flag overrides CLI_MODEL env.
uv run python -m src.main --model sonnet
# or: make run MODEL=sonnet

# Dry-run (stdout only, no Slack). CLI flag overrides DRY_RUN env.
uv run python -m src.main --model sonnet --dry-run
# or: make dry-run        (also: make smoke — the install-complete gate)

# Run weekly report
make weekly
# or: make weekly DATE=2026-04-06

# Create next week's Confluence page
make create-page
# or: make create-page DATE=2026-04-13
```

The script generates the report and posts it to the configured Slack channel. On failure it exits with a non-zero code (so cron/monitoring can detect it).

### Pinning the model in scheduled jobs

The cron template (`deploy/report.crontab.tmpl`) already prefixes each job with `CLI_MODEL=sonnet`. If `.env` also sets `CLI_MODEL=sonnet`, that's redundant but harmless and makes the intent explicit at the schedule level.

## Regression Testing (Prompt Accuracy)

The `tests/regression/` directory contains an automated harness to evaluate `daily_report.md` prompt accuracy against ground truth. Use this when modifying the prompt or evaluating new models.

### Layout

```
tests/regression/
├── fixtures/                       # Ground truth + scoring rubric (versioned)
│   ├── ground_truth_2026_05_15.json
│   └── rubric.md
├── scripts/                        # Test orchestration (versioned)
│   ├── run_regression.sh
│   ├── score_runs.py
│   └── compare_runs.py
└── runs/                           # Generated outputs (gitignored)
    └── <timestamp>/
        ├── sonnet-001.txt ... opus-003.txt
        ├── scores.csv
        └── summary.md
```

### Commands

```bash
# Run 23 dry-runs (sonnet x10 + haiku x10 + opus x3) on the ground truth date
make regression-run DATE=2026-05-15

# Score an existing runs directory against the rubric
make regression-score RUNS_DIR=tests/regression/runs/<timestamp>

# Run + score in one shot
make regression DATE=2026-05-15

# Compare two scored runs directories
make regression-compare BASE=tests/regression/runs/<base> NEW=tests/regression/runs/<new>
```

### Rubric

15-point rubric across 4 categories (see `tests/regression/fixtures/rubric.md`):
- A1–A8: Item coverage (8 points)
- B1–B3: Category classification (3 points)
- C1–C2: Hallucination / description-quote avoidance (2 points)
- D1–D2: Output format (2 points)

Adding a new ground truth fixture (different date) is straightforward: copy `ground_truth_2026_05_15.json`, update member work items, and reference it from a new `make regression-run DATE=YYYY-MM-DD` invocation.

### Reusable Skill

This regression testing workflow is also packaged as a reusable Claude Code skill at `.claude/skills/prompt-regression-testing/`. To apply the same workflow to a different project, copy the skill directory and its `templates/` to the target project, adapt the fixtures and rubric patterns, and follow the `SKILL.md` step-by-step guide.

## Testing

Install dev dependencies and run tests:

```bash
# Install dev dependencies
uv sync --all-extras

# Run all tests
make test
# or: uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Show coverage report
make coverage

# Run specific test layer
uv run pytest tests/unit/domain/
uv run pytest tests/integration/
```

## Scheduling (cron)

Scheduling is managed as code: a versioned crontab **template** is rendered with the real install paths and installed into the user crontab. No external scheduler is required.

```bash
make cron-render     # render deploy/report.crontab.tmpl -> deploy/report.crontab (real paths)
make cron-show       # review the rendered file and the currently-installed crontab
make cron-install    # back up the existing crontab, then install the rendered one
make cron-uninstall  # restore the backed-up crontab
```

The template (`deploy/report.crontab.tmpl`) schedules three jobs (Asia/Seoul):

| Job | Schedule (KST) | Command |
|-----|----------------|---------|
| Daily report | Mon–Fri 12:00 | `CLI_MODEL=sonnet uv run python -m src.main` |
| Weekly report | Mon 12:00 | `... REPORT_MODE=weekly ...` |
| Create next week's page | Mon 07:00 | `... REPORT_MODE=create_page ...` |

**Important notes (Debian/Ubuntu cron):**

- **Timezone:** stock `cron` ignores `CRON_TZ` for firing time and uses the **system** timezone. Set it once: `sudo timedatectl set-timezone Asia/Seoul && sudo systemctl restart cron`. If you cannot change the system TZ, use the `(UTC: …)` times noted in each line of the template (KST = UTC+9, no DST).
- **Auth/HOME:** each job `cd`s into the repo (so `.env` is found) and relies on the Claude CLI credentials in `~/.claude`. The crontab owner must be the same user who ran `make auth`.
- **Overwrite:** `make cron-install` replaces the whole user crontab (after backing it up to `deploy/crontab.backup`). On a dedicated server this is fine; if the user has other cron jobs, prefer an additive `/etc/cron.d/report` fragment (note: that format requires a 6th username field and root ownership).
- **Logs:** each job appends stdout/stderr to `logs/*.log` (cron mail is usually unconfigured). `make setup`/`make cron-render` create the `logs/` directory.
- **Failure visibility:** `main` exits non-zero on failure, so you can alert on cron exit codes (e.g., wrap with `chronic` from `moreutils`, or add a heartbeat check).
