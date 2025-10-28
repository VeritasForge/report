# Weekly Report Generator

This script automatically generates a weekly report by summarizing content from Confluence pages and associated JIRA tickets, and then sends the report to a specified Slack channel.

## Description

The script performs the following steps:

1.  **Reads Configuration:** It reads product information (name and Confluence URL) and a list of authors from environment variables.
2.  **Generates Reports:** For each product, it constructs a Confluence URL for the previous week's report and uses the `gemini` CLI to:
    *   Read the content of the Confluence page.
    *   Fetch details of any mentioned JIRA tickets.
    *   Summarize the content into a report with the following sections: `[진행 완료]` (Completed), `[진행 중]` (In Progress), and `[진행 대기]` (Pending).
3.  **Sends to Slack:** It consolidates the reports for all products and sends them as a single message to a configured Slack channel.

## Prerequisites

Before running the script, you need to have the following installed:

*   Python 3.x
*   [Gemini CLI](https://github.com/google/gemini-cli)
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
    CONFLUENCE_PRODUCTS='[{"name": "Product A", "url": "https://your-confluence-space.atlassian.net/wiki/spaces/PROD/pages/12345"}, {"name": "Product B", "url": "https://your-confluence-space.atlassian.net/wiki/spaces/PROD/pages/67890"}]'
    CONFLUENCE_AUTHORS="John Doe,Jane Smith"
    ```

    *   `SLACK_TOKEN`: Your Slack bot token with `chat:write` permission.
    *   `SLACK_CHANNEL`: The ID of the Slack channel where the report will be sent.
    *   `CONFLUENCE_PRODUCTS`: A JSON string containing a list of product objects. Each object must have a `name` and a `url` pointing to the Confluence page.
    *   `CONFLUENCE_AUTHORS`: A comma-separated list of author names to filter the content from the Confluence page.

## Usage

To run the script, execute the following command from the root of the project:

```bash
uv run python -m src.main
```

The script will then generate the report and post it to the specified Slack channel.



