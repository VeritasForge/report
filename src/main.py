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

def send_slack_notification(report_text: str, thread_text: str = None):
    """
    Sends a notification to a Slack channel using a bot token.
    If thread_text is provided, it will be posted as a reply in a thread.

    Args:
        report_text: The main report text to send.
        thread_text: Optional text to post as a thread reply (e.g., ticket links).
    """
    token = os.environ.get("SLACK_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL")

    if not token or not channel:
        print("WARNING: SLACK_TOKEN or SLACK_CHANNEL environment variables not set. Skipping Slack notification.")
        return

    try:
        client = WebClient(token=token)
        main_response = client.chat_postMessage(channel=channel, text=report_text)
        print(f"Successfully sent report to Slack channel '{channel}'.")

        if thread_text:
            thread_ts = main_response["ts"]
            client.chat_postMessage(
                channel=channel,
                text=thread_text,
                thread_ts=thread_ts
            )
            print(f"Successfully sent ticket links as thread reply.")
    except Exception as e:
        print(f"ERROR: An error occurred while sending report to Slack: {e}")
        raise e

def generate_report(products: str, authors: str, space_key: str, page_title: str) -> tuple[str, str] | None:
    """
    Generates a weekly report for all products from a single Confluence page using the Claude CLI.

    Args:
        products: A comma-separated list of product names (e.g., 'VC, ER, Cluon-M').
        authors: A comma-separated list of author names.
        space_key: The Confluence space key (e.g., 'MAI').
        page_title: The title of the Confluence page to search for.

    Returns:
        A tuple of (main_report, thread_ticket_links) as strings, or None if an error occurred.
    """
    print(f"Starting report generation for Space: {space_key}, Title: {page_title}")

    prompt_template = f"""
        atlassian mcp를 통해서 다음 작업을 수행해줘:
        1. Confluence에서 다음 페이지를 검색해서 읽어줘:
           - Space: {space_key}
           - 제목: {page_title}
        2. 중요: {authors} 들이 작성한 내용만 추출해서 정리해줘. 이 목록에 없는 작성자의 내용은 절대 포함하지 마.
        3. 각 프로젝트({products})에 대해 아래 형식으로 보고서를 생성해줘:

        ## 메인 보고서 형식 ##
        -- [프로젝트명] -- (예: -- VC --, -- ER --)
        [진행 완료]
        - [서비스명] (예: vc-backend, er-scoring-manager 등)
          - 작업 내용 요약 (JIRA 티켓 링크 없이 내용만)
        [진행 중]
        - [서비스명]
          - 작업 내용 요약
        [진행 대기]
        - [서비스명]
          - 작업 내용 요약

        ## 규칙 ##
        - 프로젝트별로 구분 ({products})
        - 동일한 서비스(레포지토리)의 티켓들은 그룹화해서 표시
        - 티켓이 없는 섹션은 "- 특이사항 없음"으로 표시
        - 중요: 유사한 작업은 반드시 하나로 합쳐서 표시
          예) "로그인 유닛 테스트", "계정별 설정 유닛 테스트", "글로벌 설정 유닛 테스트" → "유닛 테스트 레포트(DHF 문서) 코드 구현"
          예) "vc_event JPA Repository 정의", "vc_icu JPA Repository 정의" → "vc_event/vc_icu 관련 JPA Repository 정의"
        - 개인별 나열이 아닌 작업 내용 중심으로 정리
        - 불필요한 부연 설명 없이 간결하게 작성

        ## 티켓 링크 표시 규칙 ##
        1. 티켓이 1개인 작업: 메인 보고서에 슬랙 링크 형식으로 포함
           예) * <https://aitrics.atlassian.net/browse/VITALCARES-4409|[on-call] 대시보드 저장공간 얼럿 미표시 현상>

        2. 티켓이 2개 이상인 작업: 메인 보고서에는 제목만 표시 (링크 없이)
           예) * vc_event/vc_icu 관련 JPA Repository 정의 및 조회 기능 구현

        ## 출력 형식 ##
        반드시 아래 구분자를 사용해서 메인 보고서와 스레드용 티켓 목록을 분리해서 출력해줘:

        [메인 보고서]
        (메인 보고서 내용 - 티켓 1개는 슬랙 링크 포함, 2개 이상은 제목만)

        ---THREAD_TICKETS---

        [스레드용 티켓 목록]
        (티켓이 2개 이상인 작업들만 아래 형식으로)
        * 작업 제목:
           * https://aitrics.atlassian.net/browse/TICKET-123
           * https://aitrics.atlassian.net/browse/TICKET-456

        다른 설명이나 부가적인 말 없이, 위 형식대로만 출력해줘.
    """
    prompt = textwrap.dedent(prompt_template).strip()
    print(prompt)

    command = ['claude', '-p', prompt, "--dangerously-skip-permissions"]

    try:
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

        # Parse the output to separate main report and thread ticket links
        output = stdout.strip()
        if "---THREAD_TICKETS---" in output:
            parts = output.split("---THREAD_TICKETS---")
            main_report = parts[0].replace("[메인 보고서]", "").strip()
            thread_tickets = parts[1].replace("[스레드용 티켓 목록]", "").strip() if len(parts) > 1 else ""
            return (main_report, thread_tickets)
        else:
            return (output, "")

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

    # Page products for title (may include additional projects like Cluon-M)
    page_products = os.environ.get("CONFLUENCE_PAGE_PRODUCTS")
    if not page_products:
        page_products = products  # fallback to CONFLUENCE_PRODUCTS

    # 1. Calculate date components needed for the report
    today_for_header = datetime.now()
    formatted_date_header = today_for_header.strftime('%Y.%m.%d (%a)')
    today = date.today()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday, weeks=1)
    last_friday = last_monday + timedelta(days=4)
    date_range = f"{last_monday.strftime('%Y-%m-%d')} ~ {last_friday.strftime('%Y-%m-%d')}"

    # 2. Build page title (e.g., "Daily meeting 2025-12-08 ~ 2025-12-12 (VC, ER, Cluon-M, etc.)")
    page_title = f"{page_title_prefix} {date_range} ({page_products}, etc.)"

    # 3. Generate report from single Confluence page
    print(f"\n--------------------\nGenerating report from: {page_title}\n--------------------")
    report_header = f"""
        {formatted_date_header}
        BE 팀 주간 업무 보고 드립니다.
    """

    result = generate_report(products, authors, space_key, page_title)
    if result is None:
        print("ERROR: Failed to generate report. Skipping Slack notification.")
        return

    main_report, thread_tickets = result
    report_message = textwrap.dedent(report_header).strip() + "\n\n" + main_report
    send_slack_notification(report_message, thread_tickets if thread_tickets else None)

if __name__ == "__main__":
    main()
