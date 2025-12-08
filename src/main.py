import os
import json
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

def generate_report_for_product(product_name: str, authors: str, space_key: str, page_title: str) -> str | None:
    """
    Generates a weekly report for a single product using the Gemini CLI.

    Args:
        product_name: The name of the product.
        authors: A comma-separated list of author names.
        space_key: The Confluence space key (e.g., 'MAI').
        page_title: The title of the Confluence page to search for.

    Returns:
        The generated report as a string, or None if an error occurred.
    """
    print(f"[{product_name}] Starting report generation for Space: {space_key}, Title: {page_title}")

    prompt_template = f"""
        atlassian mcp를 통해서 다음 작업을 수행해줘:
        1. Confluence에서 다음 페이지를 검색해서 읽어줘:
           - Space: {space_key}
           - 제목: {page_title}
           - {authors} 들이 작성한 내용만 정리해줘.
        2. @GEMINI.md 지침에 따라 {product_name}에 대한 최종 보고서를 생성해줘.

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
            print(f"ERROR: [{product_name}] Gemini CLI failed with exit code {process.returncode}.")
            print(f"ERROR: [{product_name}] Stderr: {stderr.strip()}")
            return None

        print(f"[{product_name}] Report generated successfully.")
        return stdout.strip()

    except FileNotFoundError as e:
        print("ERROR: 'gemini' CLI not found. Please ensure it is installed and in your system's PATH.")
        raise e
    except Exception as e:
        print(f"ERROR: [{product_name}] An unexpected error occurred: {e}")
        raise e

def main():
    """
    Reads product information from environment variables, and for each product,
    generates a weekly report and sends it to Slack.
    """
    products_json = os.environ.get("CONFLUENCE_PRODUCTS")
    if not products_json:
        print("ERROR: CONFLUENCE_PRODUCTS environment variable is not set. Exiting.")
        return

    authors = os.environ.get("CONFLUENCE_AUTHORS")
    if not authors:
        print("ERROR: CONFLUENCE_AUTHORS environment variable is not set. Exiting.")
        return

    try:
        products = json.loads(products_json)
    except json.JSONDecodeError:
        print("ERROR: Failed to parse CONFLUENCE_PRODUCTS. Please ensure it is a valid JSON string.")
        return

    # 1. Calculate date components needed for all reports
    today_for_header = datetime.now()
    formatted_date_header = today_for_header.strftime('%Y.%m.%d (%a)')
    today = date.today()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday, weeks=1)
    last_friday = last_monday + timedelta(days=4)
    date_range = f"{last_monday.strftime('%Y-%m-%d')} ~ {last_friday.strftime('%Y-%m-%d')}"

    # 2. Loop through each product and generate/send a report
    report_header = f"""
        {formatted_date_header}
        BE 팀 주간 업무 보고 드립니다.
    """
    report_content = [textwrap.dedent(report_header).strip()]

    for product in products:
        product_name = product.get("name")
        space_key = product.get("space_key")

        if not (product_name and space_key):
            print(f"WARNING: Skipping invalid product entry in CONFLUENCE_PRODUCTS: {product}")
            continue

        page_title = f"{product_name} {date_range}"
        print(f"\n--------------------\nProcessing: {product_name}\n--------------------")
        report = generate_report_for_product(product_name, authors, space_key, page_title)
        if report is None:
            print(f"ERROR: Failed to generate report for {product_name}. Skipping Slack notification.")
            return

        report_content.append(report)

    result = "\n\n".join(report_content)
    send_slack_notification(result)

if __name__ == "__main__":
    main()
