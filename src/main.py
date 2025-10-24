import os
import json
import subprocess
import textwrap
from datetime import date, timedelta, datetime
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        client.chat_postMessage(channel=channel, text=report_text)
        print(f"Successfully sent a report to Slack channel '{channel}'.")
    except Exception as e:
        print(f"ERROR: An error occurred while sending report to Slack: {e}")
        raise e

def generate_report_for_product(product_name: str, authors: str, product_url: str, url_date_range: str) -> str | None:
    """
    Generates a weekly report for a single product using the Gemini CLI.

    Args:
        product_name: The name of the product.
        authors: A comma-separated list of author names.
        product_url: The base Confluence URL for the product.
        url_date_range: The formatted date range for the Confluence URL.

    Returns:
        The generated report as a string, or None if an error occurred.
    """
    full_url = f"{product_url}+{url_date_range}"
    print(f"[{product_name}] Starting report generation for URL: {full_url}")

    prompt_template = f"""
        atlassian mcp를 통해서 다음 작업을 수행해줘:
        1. 다음 Confluence 페이지를 읽어줘:
           - {product_name} 주간 보고: {full_url}
           - {authors} 들이 작성한 내용만 정리해줘.
        2. 페이지 내용에 언급된 모든 JIRA 티켓의 상세 내용도 읽어줘.
        3. 읽은 모든 내용을 취합하고 요약해서, 아래의 형식에 맞춰 최종 보고서를 생성해줘.
           각 섹션에 해당하는 내용을 분류해서 넣어줘.
        4. 주의!! 본 문서는 대표에게 보고하는 내용이라 단순히 티켓을 나열하면 안되고 내용을 추상화해서 정리해줘야해!!

        --- 형식 시작 ---
        {product_name}

        [진행 완료]
        ...

        [진행 중]
        ...

        [진행 대기]
        ...
        --- 형식 끝 ---

        전에 위 형식으로 출력한 결과는 다음과 같았어. 결과를 출력할때 참고하면 좋을것 같아.
        --- 이전 출력 예제 시작 ---
        25.10.10 Fri
        BE 팀 주간 업무 보고 드립니다.
        [진행 완료]
        - API 서버 로직 개선
         - 대시보드의 응답 속도 개선
        - API 버그 수정
         - demo_api에서 ID에 특수문자가 포함될 경우 발생하던 오류 해결
        [진행 중]
        - AI 서비스 연동 개발
         - AI 요청 및 응답 처리 기능 구현
         - AI 예측 결과 수정 기능 구현
        - 데이터 조회 성능 개선
         - 데이터 조회 시, 여러 시간 범위를 한 번에 처리하도록 백엔드 로직 수정
        - 리포트 기능 버그 수정
         - History 리포트에서 특정 정보가 특정 시점의 데이터가 아닌 최신 정보로 잘못 표시되는 문제
           해결 중
        [진행 대기]
        - 특이사항 없음
        --- 이전 출력 예제 끝 ---

        다른 설명이나 부가적인 말 없이, 최종적으로 생성된 보고서 텍스트만 출력해줘.
    """
    prompt = textwrap.dedent(prompt_template).strip()
    command = ['gemini', '--yolo', prompt]

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
    url_date_range = f"{last_monday.strftime('%Y-%m-%d')}+~+{last_friday.strftime('%Y-%m-%d')}"

    # 2. Loop through each product and generate/send a report
    report_header = f"""
        {formatted_date_header}
        BE 팀 주간 업무 보고 드립니다.
    """
    report_content = [textwrap.dedent(report_header).strip()]

    for product in products:
        product_name = product.get("name")
        product_url = product.get("url")

        if not product_name or not product_url:
            print(f"WARNING: Skipping invalid product entry in CONFLUENCE_PRODUCTS: {product}")
            continue

        print(f"\n--------------------\nProcessing: {product_name}\n--------------------")
        report = generate_report_for_product(product_name, authors, product_url, url_date_range)
        if report is None:
            print(f"ERROR: Failed to generate report for {product_name}. Skipping Slack notification.")
            return

        report_content.append(report)

    result = "\n\n".join(report_content)
    send_slack_notification(result)

if __name__ == "__main__":
    main()
