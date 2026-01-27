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

    예: DateRange(2026-01-27, 2026-01-31) -> "2026.01.27 ~ 31"
    """
    start = date_range.start
    end = date_range.end
    return f"{start.strftime('%Y.%m.%d')} ~ {end.strftime('%d')}"


def convert_markdown_links_to_slack(text: str) -> str:
    """
    마크다운 링크를 Slack 형식으로 변환

    [TICKET-123](url) 설명 텍스트 -> <url|[TICKET-123] 설명 텍스트>
    """
    pattern = r'\[([^\]]+)\]\(([^)]+)\)\s*(.*)$'
    return re.sub(pattern, r'<\2|[\1] \3>', text, flags=re.MULTILINE)
