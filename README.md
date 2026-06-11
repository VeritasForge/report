# Weekly Report Generator

This script automatically generates a weekly report by summarizing content from Confluence pages and associated JIRA tickets, and then sends the report to a specified Slack channel.

## Description

The script supports two modes: **daily** (default) and **weekly**.

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

Before running the script, you need to have the following installed:

*   Python 3.x
*   [uv](https://github.com/astral-sh/uv)
*   [Claude CLI](https://docs.anthropic.com/en/docs/claude-code)
*   The required Python libraries as specified in `pyproject.toml`.

## Setup

1.  **Create Virtual Environemtn and Install Dependencies:**
    ```bash
    uv sync --locked
    ```

2.  **Set Environment Variables:**
    Create a `.env` file in the root of the project and add the following variables:

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
    REPORT_MODE="daily"  # Optional, "daily" (default) or "weekly"

    # Confluence API Configuration (for create_page mode)
    CONFLUENCE_URL="https://your-instance.atlassian.net"
    CONFLUENCE_USER="your-email@company.com"
    CONFLUENCE_TOKEN="your-api-token"
    PARENT_PAGE_ID="your-parent-page-id"
    ```

    *   `SLACK_TOKEN`: Your Slack bot token with `chat:write` permission.
    *   `SLACK_CHANNEL`: The ID of the Slack channel where daily reports will be sent.
    *   `SLACK_CHANNEL_WEEKLY`: (Optional) The ID of the Slack channel for weekly reports. If not set, weekly reports are skipped (empty channel).
    *   `SLACK_CHANNEL_CREATE_PAGE`: (Optional) The ID of the Slack channel for `create_page` mode notifications (success/already-exists/failure). If not set, notifications are skipped — page creation continues normally.
    *   `CONFLUENCE_SPACE_KEY`: The Confluence space key where weekly pages are stored.
    *   `REPORT_TEAM_NAME`: (Optional) Team name to include in the report header.
    *   `REPORT_TEAM_PREFIX`: (Optional) Team prefix for Slack message title. Format: `[{prefix}][{YY.MM.DD}_Daily]` or `[{prefix}][{YY.MM.DD}_Weekly]`.
    *   `REPORT_MENTION_USERS`: (Optional) Users to mention when there are delayed or on-hold items.
    *   `CLI_TYPE`: (Optional) CLI to use for report generation. Supported value: `claude` (default).
    *   `CLI_MODEL`: (Optional) Claude model alias. Supported: `sonnet` (default & **recommended**), `haiku`, `opus`. CLI flag `--model` takes precedence. See [Recommended Model](#recommended-model) section below.
    *   `DRY_RUN`: (Optional) Truthy values (`1`, `true`, `True`) print the report to stdout instead of sending to Slack. Useful for prompt experimentation. CLI flag `--dry-run` takes precedence.
    *   `REPORT_MODE`: (Optional) Report mode. `daily` (default) generates a single day report, `weekly` generates a weekly summary.
    *   `CONFLUENCE_URL`: (Required for create_page mode) Your Confluence instance URL.
    *   `CONFLUENCE_USER`: (Required for create_page mode) Your Confluence user email.
    *   `CONFLUENCE_TOKEN`: (Required for create_page mode) Your Confluence API token.
    *   `PARENT_PAGE_ID`: (Required for create_page mode) The parent page ID where weekly pages are created.

3.  **Configure Report Commands:**
    The report generation logic is defined in `.claude/commands/daily_report.md` (daily mode) and `.claude/commands/weekly_report.md` (weekly mode). These commands are automatically executed by the CLI with the calculated date range.

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

# Explicitly specify CLI
CLI_TYPE=claude uv run python -m src.main

# Choose Claude model (sonnet/haiku/opus). CLI flag overrides CLI_MODEL env.
uv run python -m src.main --model sonnet
CLI_MODEL=haiku uv run python -m src.main
# or: make run MODEL=sonnet

# Dry-run (stdout only, no Slack). CLI flag overrides DRY_RUN env.
uv run python -m src.main --model sonnet --dry-run
DRY_RUN=1 uv run python -m src.main --model sonnet
# or: make dry-run
# or: make dry-run MODEL=sonnet DATE=2026-04-06

# Run weekly report
REPORT_MODE=weekly uv run python -m src.main
# or: make weekly

# Run weekly report for a specific week
make weekly DATE=2026-04-06

# Create next week's Confluence page
make create-page
# or: REPORT_MODE=create_page uv run python -m src.main

# Create page for a specific week
make create-page DATE=2026-04-13
```

The script will then generate the report and post it to the specified Slack channel.

### Cronicle Management

```bash
make cronicle-status   # Check if Cronicle is running
make cronicle-start    # Start Cronicle and open web UI
make cronicle-stop     # Stop Cronicle
make cronicle-restart  # Restart Cronicle and open web UI
make cronicle-open     # Open web UI in browser
```

### Cronicle Event Scripts — Pin Sonnet

When updating Cronicle events (Schedule tab), add `CLI_MODEL=sonnet` to each event's shell script to pin the recommended model. Example for the Daily Report event:

```sh
#!/bin/sh
cd /Users/cjynim/lab/report
CLI_MODEL=sonnet uv run python -m src.main
```

Same pattern for Weekly Report and Create Weekly Page:

```sh
# Weekly Report
CLI_MODEL=sonnet REPORT_MODE=weekly uv run python -m src.main

# Create Weekly Page
CLI_MODEL=sonnet REPORT_MODE=create_page uv run python -m src.main
```

Note: If `.env` already has `CLI_MODEL=sonnet`, this is redundant but harmless and makes the intent explicit at the schedule level.

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

This regression testing workflow is also packaged as a reusable Claude Code skill at `.claude/skills/prompt-regression-testing/`. To apply the same workflow to a different project (different prompt, different domain), copy the skill directory and its `templates/` to the target project, adapt the fixtures and rubric patterns, and follow the `SKILL.md` step-by-step guide. The skill captures lessons learned from this project — including model cost/time estimates, common scoring pitfalls, and the company-info generalization pattern.

## Testing

Install dev dependencies and run tests:

```bash
# Install dev dependencies
uv sync --all-extras

# Run all tests
make test
# or: uv run pytest

# Show coverage report (after running tests with --cov)
make coverage
# or: uv run coverage report --show-missing

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test layer
uv run pytest tests/unit/domain/
uv run pytest tests/integration/
```

## Scheduling

This project uses [Cronicle](https://cronicle.net/) for scheduling. Cronicle provides a web-based UI with execution history and notifications.

### 1. Install Cronicle

You install Cronicle the following command.

> curl -s https://raw.githubusercontent.com/jhuckaby/Cronicle/master/bin/install.js | sudo node

and then, you'll see the follwing message.

```sh
❯ curl -s https://raw.githubusercontent.com/jhuckaby/Cronicle/master/bin/install.js | sudo node                                                      (base)

Cronicle Installer v1.5
Copyright (c) 2015 - 2022 PixlCore.com. MIT Licensed.
Log File: /opt/cronicle/logs/install.log

Fetching release list...
Installing Cronicle v0.9.99...
Installing dependencies...
Running post-install script...

Welcome to Cronicle!
First time installing?  You should configure your settings in '/opt/cronicle/conf/config.json'.
Next, if this is a master server, type: '/opt/cronicle/bin/control.sh setup' to init storage.
Then, to start the service, type: '/opt/cronicle/bin/control.sh start'.
For full docs, please visit: http://github.com/jhuckaby/Cronicle
Enjoy!

Installation complete.
```

### 2. Setup

Change ownership so Cronicle runs as your user (not root):

```bash
sudo chown -R $(whoami):staff /opt/cronicle
```

Then initialize storage:

> /opt/cronicle/bin/control.sh setup
>
- Create the storage system (`/opt/cronicle/data`)
- Create user information in the storage system's `/opt/cronicle/data/users` path

User information can be checked through the following file, allowing you to confirm UI login details.

> Initial Password: admin

```sh
❯ tree /opt/cronicle/data/users                                                                           (base) 
/opt/cronicle/data/users
└── 34
    └── 68
        └── bc
            └── 3468bc0c4e5f6aa06c7aee62212ac18f.json
            
❯ cat /opt/cronicle/data/users/34/68/bc/3468bc0c4e5f6aa06c7aee62212ac18f.json | jq .                      (base) 
{
  "username": "admin",
  "password": "",
  "full_name": "Administrator",
  "email": "admin@cronicle.com",
  "active": 1,
  "modified": 1761699616,
  "created": 1761699616,
  "salt": "salty",
  "privileges": {
    "admin": 1
  }
}

```

### 3. Start

Execute the following script to start the Web UI.

> /opt/cronicle/bin/control.sh start

```sh
❯ /opt/cronicle/bin/control.sh start                                                                      (base)
/opt/cronicle/bin/control.sh start: Starting up Cronicle Server...
/opt/cronicle/bin/control.sh start: Cronicle Server started
```

After execution, access http://localhost:3012 and log in with admin/admin!

### 4. Set up Schedule Events

Navigate to the Schedule tab and create events using the Add Event button.

#### Daily Report

- **Title**: `Daily Report`
- **Timing**: Mon–Fri, 12:00, Asia/Seoul
- **Plugin**: Shell Script
- **Script**:
```sh
#!/bin/sh
cd /Users/cjynim/lab/report
uv run python -m src.main
```

#### Weekly Report

- **Title**: `Weekly Report`
- **Timing**: Monday, 12:00, Asia/Seoul
- **Plugin**: Shell Script
- **Script**:
```sh
#!/bin/sh
cd /Users/cjynim/lab/report
REPORT_MODE=weekly uv run python -m src.main
```

#### Create Weekly Page

- **Title**: `Create Weekly Page`
- **Timing**: Monday, 07:00, Asia/Seoul
- **Plugin**: Shell Script
- **Script**:
```sh
#!/bin/sh
cd /Users/cjynim/lab/report
REPORT_MODE=create_page uv run python -m src.main
```
