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
*   [uv](https://github.com/astral-sh/uv)    
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


## Apply Cronicle

We use [Cronicle](https://cronicle.net/) for batch job.

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

### 4. Set up Schedule Event

Navigate to the Schedule tab and create an event using the Add Event button. 
The event created here can be considered a single task in crontab.

Set the **Plugin** to Shell Script and then write the following script. 

```sh
#!/bin/sh

# Enter your shell script code here

cd /Users/cjynim/lab/report

su cjynim -c "uv run python -m src.main"
```

In **Timing**, configure the desired days and times for the event to run periodically.
