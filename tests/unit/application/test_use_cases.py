"""GenerateReportUseCase 단위 테스트 (daily/weekly 공용)"""

from datetime import date
from unittest.mock import Mock

from src.application.use_cases import GenerateReportUseCase
from src.domain.models import ReportConfig


def make_config(**overrides) -> ReportConfig:
    defaults = dict(
        space_key="MAI", team_name="Backend Team", team_prefix="BE",
        mention_users="@홍길동", report_date=date(2026, 1, 27),
    )
    defaults.update(overrides)
    return ReportConfig(**defaults)


class TestGenerateReportUseCase:
    def test_should_send_daily_title_and_extracted_content(self):
        # [Happy] Given: executor가 마커 포함 출력 반환, Daily 접미사
        executor = Mock()
        executor.execute.return_value = "분석...\n\U0001f4ca 일정 요약\n- 작업1"
        notifier = Mock()
        use_case = GenerateReportUseCase(executor, notifier, title_suffix="Daily")
        # When
        result = use_case.execute(make_config())
        # Then: 제목 [BE][26.01.27_Daily] + 마커부터 추출된 본문 전송
        assert result is True
        executor.execute.assert_called_once_with("MAI", "@홍길동", date(2026, 1, 27))
        notifier.send.assert_called_once_with(
            "[BE][26.01.27_Daily]", "\U0001f4ca 일정 요약\n- 작업1"
        )

    def test_should_send_weekly_title_when_suffix_is_weekly(self):
        # [Happy] Given: Weekly 접미사
        executor = Mock()
        executor.execute.return_value = "주간 본문"
        notifier = Mock()
        use_case = GenerateReportUseCase(executor, notifier, title_suffix="Weekly")
        # When
        use_case.execute(make_config())
        # Then
        notifier.send.assert_called_once_with("[BE][26.01.27_Weekly]", "주간 본문")

    def test_should_omit_prefix_when_team_prefix_empty(self):
        # [Boundary] Given: team_prefix 빈 문자열
        executor = Mock()
        executor.execute.return_value = "본문"
        notifier = Mock()
        use_case = GenerateReportUseCase(executor, notifier, title_suffix="Daily")
        # When
        use_case.execute(make_config(team_prefix=""))
        # Then: prefix 없이 [26.01.27_Daily]
        notifier.send.assert_called_once_with("[26.01.27_Daily]", "본문")

    def test_should_use_today_when_report_date_is_none(self):
        # [Boundary] Given: report_date None → 오늘 날짜
        executor = Mock()
        executor.execute.return_value = "본문"
        notifier = Mock()
        use_case = GenerateReportUseCase(executor, notifier, title_suffix="Daily")
        # When
        use_case.execute(make_config(report_date=None))
        # Then: 오늘 날짜 포맷이 제목에 포함
        sent_title = notifier.send.call_args[0][0]
        assert date.today().strftime("%y.%m.%d") in sent_title

    def test_should_return_false_and_skip_notify_when_executor_fails(self):
        # [Error] Given: executor가 None 반환 (CLI 실패)
        executor = Mock()
        executor.execute.return_value = None
        notifier = Mock()
        use_case = GenerateReportUseCase(executor, notifier, title_suffix="Daily")
        # When
        result = use_case.execute(make_config())
        # Then: False 반환, 알림 미전송
        assert result is False
        notifier.send.assert_not_called()
