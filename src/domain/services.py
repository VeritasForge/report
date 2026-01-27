import re
import textwrap
from datetime import date, timedelta

from .models import DateRange, ReportConfig


def calculate_last_week_range(today: date) -> DateRange:
    """지난주 월요일~금요일 날짜 범위 계산"""
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday, weeks=1)
    last_friday = last_monday + timedelta(days=4)
    return DateRange(start=last_monday, end=last_friday)


def convert_markdown_links_to_slack(text: str) -> str:
    """
    마크다운 링크를 Slack 형식으로 변환

    [TICKET-123](url) 설명 텍스트 -> <url|[TICKET-123] 설명 텍스트>
    """
    pattern = r'\[([^\]]+)\]\(([^)]+)\)\s*(.*)$'
    return re.sub(pattern, r'<\2|[\1] \3>', text, flags=re.MULTILINE)


def build_report_prompt(config: ReportConfig, date_range: DateRange) -> str:
    """보고서 생성을 위한 프롬프트 생성"""
    page_title = f"{config.page_title_prefix} {date_range.format()} ({config.page_products}, etc.)"
    prompt_template = f"""
        atlassian mcp를 통해서 다음 작업을 수행해줘:
        1. Confluence에서 다음 페이지를 검색해서 읽어줘:
           - Space: {config.space_key}
           - 제목: {page_title}
        2. 중요: {config.authors} 들이 작성한 내용만 추출해서 정리해줘. 이 목록에 없는 작성자의 내용은 절대 포함하지 마.
        3. 각 프로젝트({config.products})에 대해 아래 형식으로 보고서를 생성해줘:

        ## 메인 보고서 형식 ##
        -- [프로젝트명] -- (예: -- ProjectA --, -- ProjectB --)
        [진행 완료]
        - [서비스명] (예: backend-service, data-processor 등)
          - 작업 내용 요약 (JIRA 티켓 링크 없이 내용만)
        [진행 중]
        - [서비스명]
          - 작업 내용 요약
        [진행 대기]
        - [서비스명]
          - 작업 내용 요약

        ## 규칙 ##
        - 프로젝트별로 구분 ({config.products})
        - 동일한 서비스(레포지토리)의 티켓들은 그룹화해서 표시
        - 티켓이 없는 섹션은 "- 특이사항 없음"으로 표시
        - 중요: 유사한 작업은 반드시 하나로 합쳐서 표시
          예) "로그인 유닛 테스트", "계정별 설정 유닛 테스트", "글로벌 설정 유닛 테스트" → "유닛 테스트 코드 구현"
          예) "module_a Repository 정의", "module_b Repository 정의" → "module_a/module_b 관련 Repository 정의"
        - 개인별 나열이 아닌 작업 내용 중심으로 정리
        - 불필요한 부연 설명 없이 간결하게 작성

        ## 티켓 링크 표시 규칙 ##
        1. 티켓이 1개인 작업: 메인 보고서에 슬랙 링크 형식으로 포함
           예) * <https://your-domain.atlassian.net/browse/PROJECT-123|[on-call] 대시보드 이슈 수정>

        2. 티켓이 2개 이상인 작업: 메인 보고서에는 제목만 표시 (링크 없이)
           예) * module_a/module_b 관련 Repository 정의 및 조회 기능 구현

        ## 출력 형식 ##
        반드시 아래 구분자를 사용해서 메인 보고서와 스레드용 티켓 목록을 분리해서 출력해줘:

        [메인 보고서]
        (메인 보고서 내용 - 티켓 1개는 슬랙 링크 포함, 2개 이상은 제목만)

        ---THREAD_TICKETS---

        [스레드용 티켓 목록]
        (티켓이 2개 이상인 작업들만 아래 형식으로)
        * 작업 제목:
           * https://your-domain.atlassian.net/browse/PROJECT-123
           * https://your-domain.atlassian.net/browse/PROJECT-456

        다른 설명이나 부가적인 말 없이, 위 형식대로만 출력해줘.
    """
    return textwrap.dedent(prompt_template).strip()
