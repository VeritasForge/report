# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weekly Report Generator - a Python script that automatically generates weekly reports by summarizing Confluence pages and associated JIRA tickets using the Gemini CLI, then sends reports to Slack.

## Commands

### Setup
```bash
uv sync --locked
```

### Run
```bash
uv run python -m src.main
```

## Architecture

The application is a single-module Python script (`src/main.py`) with this flow:

1. Load environment configuration (products, authors, Slack credentials)
2. Calculate the previous week's date range (Monday-Friday)
3. For each configured product:
   - Construct Confluence URL with date range
   - Call Gemini CLI with a prompt to read Confluence/JIRA and generate summary
4. Consolidate all product reports and send to Slack

### External Dependencies
- **Gemini CLI**: Must be installed separately and available in PATH. Used to read Confluence pages via Atlassian MCP and summarize content
- **Slack SDK**: For posting reports to Slack channels

## Environment Variables

Required in `.env`:
- `SLACK_TOKEN` - Slack bot token with `chat:write` permission
- `SLACK_CHANNEL` - Target Slack channel ID
- `CONFLUENCE_PRODUCTS` - JSON array of `{"name": "VC", "space_key": "MAI"}` (name is used in page title search)
- `CONFLUENCE_AUTHORS` - Comma-separated author names to filter content
