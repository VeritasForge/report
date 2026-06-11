import re
from datetime import date, timedelta

from .models import DateRange


def calculate_last_week_range(today: date) -> DateRange:
    """지난주 월요일~금요일 날짜 범위 계산"""
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday, weeks=1)
    last_friday = last_monday + timedelta(days=4)
    return DateRange(start=last_monday, end=last_friday)


def calculate_this_week_range(today: date) -> DateRange:
    """이번주 월요일~금요일 날짜 범위 계산"""
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    this_friday = this_monday + timedelta(days=4)
    return DateRange(start=this_monday, end=this_friday)


def format_confluence_page_title(date_range: DateRange) -> str:
    """
    날짜 범위를 Confluence 페이지 제목 형식으로 변환

    예: DateRange(2026-01-27, 2026-01-31) -> "2026.01.27 ~ 01.31"
    """
    start = date_range.start
    end = date_range.end
    return f"{start.strftime('%Y.%m.%d')} ~ {end.strftime('%m.%d')}"


_REPORT_MARKERS = (
    "*\U0001f4ca 일정 요약*", "*:bar_chart: 일정 요약*",
    "\U0001f4ca 일정 요약", ":bar_chart: 일정 요약",
    "*\U0001f4ca 주간 요약", "*:bar_chart: 주간 요약",
)


def extract_report_content(output: str) -> str:
    """CLI 출력에서 최종 리포트만 추출.

    리포트는 '📊 일정 요약' 등 마커로 시작한다. 중간 분석 과정이
    포함된 경우 마커 시작점부터만 추출하고, 마커가 없으면 전체 반환.
    """
    content = output.strip()
    for marker in _REPORT_MARKERS:
        idx = content.find(marker)
        if idx != -1:
            return content[idx:].strip()
    return content


def convert_markdown_links_to_slack(text: str) -> str:
    """
    마크다운 링크를 Slack 형식으로 변환

    [TICKET-123](url) 설명 텍스트 -> <url|[TICKET-123] 설명 텍스트>
    """
    pattern = r'\[([^\]]+)\]\(([^)]+)\)\s*(.*)$'
    return re.sub(pattern, r'<\2|[\1] \3>', text, flags=re.MULTILINE)
