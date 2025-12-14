import os
import re
import subprocess
import textwrap
from datetime import date, timedelta, datetime
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def convert_markdown_links_to_slack(text: str) -> str:
    """
    Converts markdown links to Slack link format.

    [TICKET-123](url) 설명 텍스트 -> <url|[TICKET-123] 설명 텍스트>
    """
    pattern = r'\[([^\]]+)\]\(([^)]+)\)\s*(.*)$'
    return re.sub(pattern, r'<\2|[\1] \3>', text, flags=re.MULTILINE)

def send_slack_notification(report_text: str):
    """
    Sends a notification to a Slack channel using a bot token.

    Args:
        report_text: The text of the report to send.
    """
    token = os.environ.get("SLACK_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL")

    if not token or not channel:
        print("WARNING: SLACK_TOKEN or SLACK_CHANNEL environment variables not set. Skipping Slack notification.")
        return

    try:
        client = WebClient(token=token)
        slack_formatted_text = convert_markdown_links_to_slack(report_text)
        client.chat_postMessage(channel=channel, text=slack_formatted_text)
        print(f"Successfully sent a report to Slack channel '{channel}'.")
    except Exception as e:
        print(f"ERROR: An error occurred while sending report to Slack: {e}")
        raise e

def generate_report(products: str, authors: str, space_key: str, page_title: str) -> str | None:
    """
    Generates a weekly report for all products from a single Confluence page using the Claude CLI.

    Args:
        products: A comma-separated list of product names (e.g., 'VC, ER, Cluon-M').
        authors: A comma-separated list of author names.
        space_key: The Confluence space key (e.g., 'MAI').
        page_title: The title of the Confluence page to search for.

    Returns:
        The generated report as a string, or None if an error occurred.
    """
    print(f"Starting report generation for Space: {space_key}, Title: {page_title}")

    prompt_template = f"""
        atlassian mcp를 통해서 다음 작업을 수행해줘:
        1. Confluence에서 다음 페이지를 검색해서 읽어줘:
           - Space: {space_key}
           - 제목: {page_title}
        2. 중요: {authors} 들이 작성한 내용만 추출해서 정리해줘. 이 목록에 없는 작성자의 내용은 절대 포함하지 마.
        3. 각 프로젝트({products})에 대해 아래 형식으로 보고서를 생성해줘:

        ## 보고서 형식 ##
        [프로젝트명] (예: VC, ER)
        [진행 완료]
        - [서비스명] (예: vc-backend, er-scoring-manager 등)
          - [JIRA티켓번호](JIRA링크URL) JIRA티켓제목
        [진행 중]
        - [서비스명]
          - [JIRA티켓번호](JIRA링크URL) JIRA티켓제목
        [진행 대기]
        - [서비스명]
          - [JIRA티켓번호](JIRA링크URL) JIRA티켓제목

        ## 규칙 ##
        - 프로젝트별로 구분 (VC, ER)
        - 동일한 서비스(레포지토리)의 티켓들은 그룹화해서 표시
        - 티켓이 없는 섹션은 "- 특이사항 없음"으로 표시
        - JIRA 티켓은 마크다운 링크 형식으로 표시: [TICKET-123](https://aitrics.atlassian.net/browse/TICKET-123) 티켓제목
        - JIRA 티켓의 실제 제목(summary)을 atlassian mcp로 조회해서 표시
        - 개인별 나열이 아닌 티켓 중심으로 정리
        - 불필요한 부연 설명 없이 간결하게 작성

        다른 설명이나 부가적인 말 없이, 최종적으로 생성된 보고서 텍스트만 출력해줘.
    """
    prompt = textwrap.dedent(prompt_template).strip()
    # print(prompt)

    command = ['claude', '-p', prompt, "--dangerously-skip-permissions"]

    try:
        # Using Popen to potentially stream output in the future if needed
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"ERROR: Claude CLI failed with exit code {process.returncode}.")
            print(f"ERROR: Stderr: {stderr.strip()}")
            return None

        print("Report generated successfully.")
        return stdout.strip()

    except FileNotFoundError as e:
        print("ERROR: 'claude' CLI not found. Please ensure it is installed and in your system's PATH.")
        raise e
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        raise e

def main():
    """
    Reads configuration from environment variables, generates a weekly report
    from a single Confluence page, and sends it to Slack.
    """
    space_key = os.environ.get("CONFLUENCE_SPACE_KEY")
    if not space_key:
        print("ERROR: CONFLUENCE_SPACE_KEY environment variable is not set. Exiting.")
        return

    page_title_prefix = os.environ.get("CONFLUENCE_PAGE_TITLE_PREFIX")
    if not page_title_prefix:
        print("ERROR: CONFLUENCE_PAGE_TITLE_PREFIX environment variable is not set. Exiting.")
        return

    products = os.environ.get("CONFLUENCE_PRODUCTS")
    if not products:
        print("ERROR: CONFLUENCE_PRODUCTS environment variable is not set. Exiting.")
        return

    authors = os.environ.get("CONFLUENCE_AUTHORS")
    if not authors:
        print("ERROR: CONFLUENCE_AUTHORS environment variable is not set. Exiting.")
        return

    # 1. Calculate date components needed for the report
    today_for_header = datetime.now()
    formatted_date_header = today_for_header.strftime('%Y.%m.%d (%a)')
    today = date.today()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday, weeks=1)
    last_friday = last_monday + timedelta(days=4)
    date_range = f"{last_monday.strftime('%Y-%m-%d')} ~ {last_friday.strftime('%Y-%m-%d')}"

    # 2. Build page title (e.g., "Daily meeting 2025-12-08 ~ 2025-12-12 VC ER Cluon-M etc.")
    products_for_title = products.replace(", ", " ").replace(",", " ")
    page_title = f"{page_title_prefix} {date_range} {products_for_title} etc."

    # 3. Generate report from single Confluence page
    print(f"\n--------------------\nGenerating report from: {page_title}\n--------------------")
    report_header = f"""
        {formatted_date_header}
        BE 팀 주간 업무 보고 드립니다.
    """

    report = generate_report(products, authors, space_key, page_title)
    if report is None:
        print("ERROR: Failed to generate report. Skipping Slack notification.")
        return

    result = textwrap.dedent(report_header).strip() + "\n\n" + report
    send_slack_notification(result)

if __name__ == "__main__":
    main()
