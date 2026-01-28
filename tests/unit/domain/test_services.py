"""Domain 서비스 테스트"""

from datetime import date

import pytest

from src.domain.models import DateRange
from src.domain.services import (
    calculate_last_week_range,
    calculate_this_week_range,
    convert_markdown_links_to_slack,
    format_confluence_page_title,
)


class TestCalculateLastWeekRange:
    """지난주 날짜 범위 계산 테스트"""

    @pytest.mark.parametrize(
        "today,expected_monday,expected_friday",
        [
            # 화요일 기준 → 지난주 월~금
            (date(2026, 1, 28), date(2026, 1, 19), date(2026, 1, 23)),
            # 월요일 기준 → 지난주 월~금
            (date(2026, 1, 27), date(2026, 1, 19), date(2026, 1, 23)),
            # 금요일 기준 → 지난주 월~금
            (date(2026, 1, 30), date(2026, 1, 19), date(2026, 1, 23)),
            # 토요일 기준 → 지난주 월~금
            (date(2026, 1, 31), date(2026, 1, 19), date(2026, 1, 23)),
            # 일요일 기준 → 지난주 월~금
            (date(2026, 2, 1), date(2026, 1, 19), date(2026, 1, 23)),
        ],
    )
    def test_should_calculate_last_week_range(
        self, today, expected_monday, expected_friday
    ):
        # Given: 특정 날짜가 주어졌을 때

        # When: 지난주 범위를 계산하면
        result = calculate_last_week_range(today)

        # Then: 지난주 월요일~금요일을 반환한다
        assert result.start == expected_monday
        assert result.end == expected_friday

    def test_should_return_date_range_type(self):
        # Given: 오늘 날짜가 주어졌을 때
        today = date(2026, 1, 28)

        # When: 지난주 범위를 계산하면
        result = calculate_last_week_range(today)

        # Then: DateRange 타입을 반환한다
        assert isinstance(result, DateRange)

    def test_should_handle_year_boundary(self):
        # Given: 연초 날짜가 주어졌을 때 (2026년 1월 5일 월요일)
        today = date(2026, 1, 5)

        # When: 지난주 범위를 계산하면
        result = calculate_last_week_range(today)

        # Then: 작년 12월의 날짜를 반환한다
        assert result.start == date(2025, 12, 29)
        assert result.end == date(2026, 1, 2)


class TestCalculateThisWeekRange:
    """이번주 날짜 범위 계산 테스트"""

    @pytest.mark.parametrize(
        "today,expected_monday,expected_friday",
        [
            # 2026년 1월: 26(월), 27(화), 28(수), 29(목), 30(금), 31(토)
            # 화요일 기준 → 이번주 월~금
            (date(2026, 1, 27), date(2026, 1, 26), date(2026, 1, 30)),
            # 월요일 기준 → 이번주 월~금
            (date(2026, 1, 26), date(2026, 1, 26), date(2026, 1, 30)),
            # 금요일 기준 → 이번주 월~금
            (date(2026, 1, 30), date(2026, 1, 26), date(2026, 1, 30)),
            # 수요일 기준 → 이번주 월~금
            (date(2026, 1, 28), date(2026, 1, 26), date(2026, 1, 30)),
        ],
    )
    def test_should_calculate_this_week_range(
        self, today, expected_monday, expected_friday
    ):
        # Given: 특정 날짜가 주어졌을 때

        # When: 이번주 범위를 계산하면
        result = calculate_this_week_range(today)

        # Then: 이번주 월요일~금요일을 반환한다
        assert result.start == expected_monday
        assert result.end == expected_friday

    def test_should_return_date_range_type(self):
        # Given: 오늘 날짜가 주어졌을 때
        today = date(2026, 1, 28)

        # When: 이번주 범위를 계산하면
        result = calculate_this_week_range(today)

        # Then: DateRange 타입을 반환한다
        assert isinstance(result, DateRange)

    @pytest.mark.parametrize(
        "today,expected_monday",
        [
            # 2026년 2월 1일은 일요일, 해당 주 월요일은 1월 26일
            (date(2026, 2, 1), date(2026, 1, 26)),  # 일요일
            # 2026년 1월 31일은 토요일, 해당 주 월요일은 1월 26일
            (date(2026, 1, 31), date(2026, 1, 26)),  # 토요일
        ],
    )
    def test_should_handle_weekend(self, today, expected_monday):
        # Given: 주말 날짜가 주어졌을 때

        # When: 이번주 범위를 계산하면
        result = calculate_this_week_range(today)

        # Then: 해당 주의 월요일을 반환한다
        assert result.start == expected_monday


class TestFormatConfluencePageTitle:
    """Confluence 페이지 제목 포맷 테스트"""

    def test_should_format_page_title_within_same_month(self, sample_date_range):
        # Given: 같은 달의 날짜 범위가 주어졌을 때 (2026-01-27 ~ 2026-01-31)

        # When: 페이지 제목으로 포맷하면
        result = format_confluence_page_title(sample_date_range)

        # Then: "YYYY.MM.DD ~ DD" 형식을 반환한다
        assert result == "2026.01.27 ~ 31"

    @pytest.mark.parametrize(
        "start,end,expected",
        [
            (date(2026, 1, 27), date(2026, 1, 31), "2026.01.27 ~ 31"),
            (date(2026, 2, 3), date(2026, 2, 7), "2026.02.03 ~ 07"),
            (date(2025, 12, 29), date(2026, 1, 2), "2025.12.29 ~ 02"),
        ],
    )
    def test_should_format_various_date_ranges(self, start, end, expected):
        # Given: 다양한 날짜 범위가 주어졌을 때
        date_range = DateRange(start=start, end=end)

        # When: 페이지 제목으로 포맷하면
        result = format_confluence_page_title(date_range)

        # Then: 올바른 형식을 반환한다
        assert result == expected


class TestConvertMarkdownLinksToSlack:
    """마크다운 링크 → Slack 링크 변환 테스트"""

    def test_should_convert_simple_link(self):
        # Given: 마크다운 링크가 주어졌을 때
        text = "[TICKET-123](https://jira.example.com/TICKET-123) Fix bug"

        # When: Slack 형식으로 변환하면
        result = convert_markdown_links_to_slack(text)

        # Then: Slack 링크 형식으로 변환된다
        assert result == "<https://jira.example.com/TICKET-123|[TICKET-123] Fix bug>"

    def test_should_convert_multiple_links_multiline(self):
        # Given: 여러 줄의 마크다운 링크가 주어졌을 때
        text = """[TICKET-123](https://jira.example.com/TICKET-123) First task
[TICKET-456](https://jira.example.com/TICKET-456) Second task"""

        # When: Slack 형식으로 변환하면
        result = convert_markdown_links_to_slack(text)

        # Then: 모든 링크가 변환된다
        assert "<https://jira.example.com/TICKET-123|[TICKET-123] First task>" in result
        assert (
            "<https://jira.example.com/TICKET-456|[TICKET-456] Second task>" in result
        )

    def test_should_preserve_text_without_links(self):
        # Given: 링크가 없는 텍스트가 주어졌을 때
        text = "This is plain text without any links."

        # When: Slack 형식으로 변환하면
        result = convert_markdown_links_to_slack(text)

        # Then: 텍스트가 그대로 유지된다
        assert result == text

    def test_should_handle_link_with_special_characters_in_description(self):
        # Given: 설명에 특수문자가 포함된 링크가 주어졌을 때
        text = "[TICKET-123](https://jira.example.com/TICKET-123) Fix: critical bug!"

        # When: Slack 형식으로 변환하면
        result = convert_markdown_links_to_slack(text)

        # Then: 특수문자가 포함된 설명이 유지된다
        assert (
            result
            == "<https://jira.example.com/TICKET-123|[TICKET-123] Fix: critical bug!>"
        )

    def test_should_handle_empty_description(self):
        # Given: 설명이 없는 링크가 주어졌을 때
        text = "[TICKET-123](https://jira.example.com/TICKET-123)"

        # When: Slack 형식으로 변환하면
        result = convert_markdown_links_to_slack(text)

        # Then: 빈 설명으로 변환된다
        assert result == "<https://jira.example.com/TICKET-123|[TICKET-123] >"

    def test_should_handle_mixed_content(self):
        # Given: 링크와 일반 텍스트가 섞인 콘텐츠가 주어졌을 때
        text = """## Progress
[TICKET-123](https://jira.example.com/TICKET-123) Complete feature
Some notes here
[TICKET-456](https://jira.example.com/TICKET-456) Review pending"""

        # When: Slack 형식으로 변환하면
        result = convert_markdown_links_to_slack(text)

        # Then: 링크만 변환되고 나머지는 유지된다
        assert "## Progress" in result
        assert "Some notes here" in result
        assert (
            "<https://jira.example.com/TICKET-123|[TICKET-123] Complete feature>"
            in result
        )
        assert (
            "<https://jira.example.com/TICKET-456|[TICKET-456] Review pending>" in result
        )
