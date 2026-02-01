# Weekly Report Generator

This script automatically generates a weekly report by summarizing content from Confluence pages and associated JIRA tickets, and then sends the report to a specified Slack channel.

## Description

The script supports two modes: **daily** (default) and **weekly**.

### Daily Mode
1.  **Calculates Date Range:** Automatically determines this week's date range (Monday to Friday).
2.  **Generates Reports:** Uses the `/daily_report` command via CLI tool (Claude or Gemini) to:
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
*   [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) or [Gemini CLI](https://github.com/google-gemini/gemini-cli) (at least one required)
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

    # Confluence Configuration
    CONFLUENCE_SPACE_KEY="MAI"

    # Report Configuration
    REPORT_TEAM_NAME="Backend Team"  # Optional, used in report header
    REPORT_TEAM_PREFIX="BE"  # Optional, team prefix for Slack message title (e.g., [BE][26.01.27_Daily])
    REPORT_MENTION_USERS="@홍길동 @김철수"  # Optional, users to mention on delay/hold items

    # CLI Configuration
    CLI_TYPE="claude"  # Optional, "claude" (default) or "gemini"

    # Report Mode
    REPORT_MODE="daily"  # Optional, "daily" (default) or "weekly"
    ```

    *   `SLACK_TOKEN`: Your Slack bot token with `chat:write` permission.
    *   `SLACK_CHANNEL`: The ID of the Slack channel where the report will be sent.
    *   `CONFLUENCE_SPACE_KEY`: The Confluence space key where weekly pages are stored.
    *   `REPORT_TEAM_NAME`: (Optional) Team name to include in the report header.
    *   `REPORT_TEAM_PREFIX`: (Optional) Team prefix for Slack message title. Format: `[{prefix}][{YY.MM.DD}_Daily]` or `[{prefix}][{YY.MM.DD}_Weekly]`.
    *   `REPORT_MENTION_USERS`: (Optional) Users to mention when there are delayed or on-hold items.
    *   `CLI_TYPE`: (Optional) CLI to use for report generation. Supported values: `claude` (default), `gemini`.
    *   `REPORT_MODE`: (Optional) Report mode. `daily` (default) generates a single day report, `weekly` generates a weekly summary.

3.  **Configure Report Commands:**
    The report generation logic is defined in `.claude/commands/daily_report.md` (daily mode) and `.claude/commands/weekly_report.md` (weekly mode). These commands are automatically executed by the CLI with the calculated date range.

## Usage

To run the script, execute the following command from the root of the project:

```bash
# Run daily report (default)
uv run python -m src.main
# or: make run

# Explicitly specify CLI
CLI_TYPE=claude uv run python -m src.main
CLI_TYPE=gemini uv run python -m src.main

# Run weekly report
REPORT_MODE=weekly uv run python -m src.main
# or: make weekly
```

The script will then generate the report and post it to the specified Slack channel.

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

Executing the script below will: 

> sudo /opt/cronicle/bin/control.sh setup
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

> sudo /opt/cronicle/bin/control.sh start

```sh
❯ sudo /opt/cronicle/bin/control.sh start                                                                 (base) 
Password:
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
su cjynim -c "uv run python -m src.main"
```

#### Weekly Report

- **Title**: `Weekly Report`
- **Timing**: Monday, 12:00, Asia/Seoul
- **Plugin**: Shell Script
- **Script**:
```sh
#!/bin/sh
cd /Users/cjynim/lab/report
su cjynim -c "REPORT_MODE=weekly uv run python -m src.main"
```
