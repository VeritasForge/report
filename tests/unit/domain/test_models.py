"""Domain 모델 테스트"""

from datetime import date

import pytest

from src.domain.models import DateRange, Report, ReportConfig


class TestDateRange:
    """DateRange 값 객체 테스트"""

    def test_should_create_date_range_with_start_and_end(self):
        # Given: 시작일과 종료일이 주어졌을 때
        start = date(2026, 1, 27)
        end = date(2026, 1, 31)

        # When: DateRange를 생성하면
        date_range = DateRange(start=start, end=end)

        # Then: 시작일과 종료일이 올바르게 설정된다
        assert date_range.start == start
        assert date_range.end == end

    def test_should_format_date_range_as_string(self, sample_date_range):
        # Given: 2026-01-27 ~ 2026-01-31 날짜 범위가 주어졌을 때

        # When: format() 메서드를 호출하면
        result = sample_date_range.format()

        # Then: "YYYY-MM-DD ~ YYYY-MM-DD" 형식의 문자열을 반환한다
        assert result == "2026-01-27 ~ 2026-01-31"

    @pytest.mark.parametrize(
        "start,end,expected",
        [
            (date(2026, 1, 1), date(2026, 1, 5), "2026-01-01 ~ 2026-01-05"),
            (date(2025, 12, 29), date(2026, 1, 2), "2025-12-29 ~ 2026-01-02"),
            (date(2026, 2, 1), date(2026, 2, 28), "2026-02-01 ~ 2026-02-28"),
        ],
    )
    def test_should_format_various_date_ranges(self, start, end, expected):
        # Given: 다양한 날짜 범위가 주어졌을 때
        date_range = DateRange(start=start, end=end)

        # When: format() 메서드를 호출하면
        result = date_range.format()

        # Then: 올바른 형식의 문자열을 반환한다
        assert result == expected

    def test_should_be_immutable(self, sample_date_range):
        # Given: frozen=True로 생성된 DateRange가 주어졌을 때

        # When/Then: 속성을 수정하려고 하면 에러가 발생한다
        with pytest.raises(AttributeError):
            sample_date_range.start = date(2026, 1, 1)


class TestReportConfig:
    """ReportConfig 설정 객체 테스트"""

    def test_should_create_report_config_with_all_fields(self, sample_report_config):
        # Given/When: 모든 필드가 설정된 ReportConfig가 주어졌을 때

        # Then: 모든 필드가 올바르게 설정된다
        assert sample_report_config.space_key == "MAI"
        assert sample_report_config.team_name == "Backend Team"
        assert sample_report_config.team_prefix == "BE"
        assert sample_report_config.mention_users == "@홍길동 @김철수"

    def test_should_create_report_config_with_minimal_fields(
        self, sample_report_config_minimal
    ):
        # Given/When: 최소 필드만 설정된 ReportConfig가 주어졌을 때

        # Then: 빈 문자열로 설정된다
        assert sample_report_config_minimal.space_key == "MAI"
        assert sample_report_config_minimal.team_name == ""
        assert sample_report_config_minimal.team_prefix == ""
        assert sample_report_config_minimal.mention_users == ""

    def test_should_be_immutable(self, sample_report_config):
        # Given: frozen=True로 생성된 ReportConfig가 주어졌을 때

        # When/Then: 속성을 수정하려고 하면 에러가 발생한다
        with pytest.raises(AttributeError):
            sample_report_config.space_key = "NEW"


class TestReport:
    """Report 엔티티 테스트"""

    def test_should_create_report_with_main_content_only(self):
        # Given: 메인 콘텐츠만 주어졌을 때
        content = "# Report Content"

        # When: Report를 생성하면
        report = Report(main_content=content)

        # Then: 메인 콘텐츠가 설정되고 thread_tickets는 None이다
        assert report.main_content == content
        assert report.thread_tickets is None

    def test_should_create_report_with_thread_tickets(self, sample_report_with_tickets):
        # Given/When: thread_tickets가 포함된 Report가 주어졌을 때

        # Then: 모든 필드가 올바르게 설정된다
        assert "Daily Report" in sample_report_with_tickets.main_content
        assert "TICKET-123" in sample_report_with_tickets.thread_tickets

    def test_should_be_mutable(self, sample_report):
        # Given: Report가 주어졌을 때 (frozen=False)
        new_content = "Updated content"

        # When: 속성을 수정하면
        sample_report.main_content = new_content

        # Then: 속성이 수정된다
        assert sample_report.main_content == new_content
