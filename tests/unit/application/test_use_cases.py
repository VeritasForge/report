"""Application 유스케이스 테스트"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.application.use_cases import GenerateWeeklyReportUseCase
from src.domain.models import Report, ReportConfig


class TestGenerateWeeklyReportUseCase:
    """주간 보고서 생성 유스케이스 테스트"""

    @pytest.fixture
    def mock_report_generator(self):
        """Mock ReportGeneratorPort"""
        return MagicMock()

    @pytest.fixture
    def mock_notifier(self):
        """Mock NotificationPort"""
        return MagicMock()

    @pytest.fixture
    def use_case(self, mock_report_generator, mock_notifier):
        """테스트용 유스케이스 인스턴스"""
        return GenerateWeeklyReportUseCase(
            report_generator=mock_report_generator,
            notifier=mock_notifier,
        )

    def test_should_generate_and_send_report_successfully(
        self,
        use_case,
        mock_report_generator,
        mock_notifier,
        sample_report_config,
        sample_report,
    ):
        # Given: 보고서 생성이 성공적으로 완료되는 상황
        mock_report_generator.generate.return_value = sample_report

        # When: 유스케이스를 실행하면
        result = use_case.execute(sample_report_config)

        # Then: True를 반환하고, 보고서가 생성되고 전송된다
        assert result is True
        mock_report_generator.generate.assert_called_once_with(sample_report_config)
        mock_notifier.send.assert_called_once()

    def test_should_return_false_when_report_generation_fails(
        self, use_case, mock_report_generator, mock_notifier, sample_report_config
    ):
        # Given: 보고서 생성이 실패하는 상황
        mock_report_generator.generate.return_value = None

        # When: 유스케이스를 실행하면
        result = use_case.execute(sample_report_config)

        # Then: False를 반환하고, 알림이 전송되지 않는다
        assert result is False
        mock_notifier.send.assert_not_called()

    def test_should_send_report_content_as_thread_message(
        self,
        use_case,
        mock_report_generator,
        mock_notifier,
        sample_report_config,
        sample_report,
    ):
        # Given: 보고서가 생성된 상황
        mock_report_generator.generate.return_value = sample_report

        # When: 유스케이스를 실행하면
        use_case.execute(sample_report_config)

        # Then: 메인 메시지(제목)와 스레드 메시지(보고서 내용)가 전송된다
        call_args = mock_notifier.send.call_args
        assert call_args[0][1] == sample_report.main_content  # thread_message

    @patch("src.application.use_cases.datetime")
    def test_should_build_title_with_team_prefix(
        self,
        mock_datetime,
        use_case,
        mock_report_generator,
        mock_notifier,
        sample_report_config,
        sample_report,
    ):
        # Given: 팀 접두사가 있고 특정 날짜인 상황
        mock_datetime.now.return_value = datetime(2026, 1, 27)
        mock_report_generator.generate.return_value = sample_report

        # When: 유스케이스를 실행하면
        use_case.execute(sample_report_config)

        # Then: "[BE][26.01.27_Daily]" 형식의 제목이 전송된다
        call_args = mock_notifier.send.call_args
        assert call_args[0][0] == "[BE][26.01.27_Daily]"

    @patch("src.application.use_cases.datetime")
    def test_should_build_title_without_team_prefix(
        self,
        mock_datetime,
        use_case,
        mock_report_generator,
        mock_notifier,
        sample_report_config_minimal,
        sample_report,
    ):
        # Given: 팀 접두사가 없는 상황
        mock_datetime.now.return_value = datetime(2026, 1, 27)
        mock_report_generator.generate.return_value = sample_report

        # When: 유스케이스를 실행하면
        use_case.execute(sample_report_config_minimal)

        # Then: "[26.01.27_Daily]" 형식의 제목이 전송된다 (접두사 없음)
        call_args = mock_notifier.send.call_args
        assert call_args[0][0] == "[26.01.27_Daily]"

    def test_should_call_generator_with_correct_config(
        self,
        use_case,
        mock_report_generator,
        mock_notifier,
        sample_report_config,
        sample_report,
    ):
        # Given: 설정이 주어진 상황
        mock_report_generator.generate.return_value = sample_report

        # When: 유스케이스를 실행하면
        use_case.execute(sample_report_config)

        # Then: 올바른 설정으로 보고서 생성이 호출된다
        mock_report_generator.generate.assert_called_once_with(sample_report_config)

    @patch("src.application.use_cases.datetime")
    def test_should_format_date_correctly_in_title(
        self,
        mock_datetime,
        use_case,
        mock_report_generator,
        mock_notifier,
        sample_report_config,
        sample_report,
    ):
        # Given: 특정 날짜가 주어진 상황
        mock_datetime.now.return_value = datetime(2026, 12, 31)
        mock_report_generator.generate.return_value = sample_report

        # When: 유스케이스를 실행하면
        use_case.execute(sample_report_config)

        # Then: 날짜가 올바르게 포맷된다 (YY.MM.DD)
        call_args = mock_notifier.send.call_args
        assert "[26.12.31_Daily]" in call_args[0][0]


class TestBuildTitle:
    """제목 생성 메서드 테스트"""

    @pytest.fixture
    def use_case(self):
        """테스트용 유스케이스 인스턴스 (의존성 Mock)"""
        return GenerateWeeklyReportUseCase(
            report_generator=MagicMock(),
            notifier=MagicMock(),
        )

    @patch("src.application.use_cases.datetime")
    def test_should_include_prefix_when_provided(
        self, mock_datetime, use_case, sample_report_config
    ):
        # Given: 팀 접두사가 있는 설정
        mock_datetime.now.return_value = datetime(2026, 1, 27)

        # When: 제목을 생성하면
        result = use_case._build_title(sample_report_config)

        # Then: 접두사가 포함된 제목이 생성된다
        assert result == "[BE][26.01.27_Daily]"

    @patch("src.application.use_cases.datetime")
    def test_should_exclude_prefix_when_empty(
        self, mock_datetime, use_case, sample_report_config_minimal
    ):
        # Given: 팀 접두사가 없는 설정
        mock_datetime.now.return_value = datetime(2026, 1, 27)

        # When: 제목을 생성하면
        result = use_case._build_title(sample_report_config_minimal)

        # Then: 접두사 없이 제목이 생성된다
        assert result == "[26.01.27_Daily]"

    @patch("src.application.use_cases.datetime")
    @pytest.mark.parametrize(
        "prefix,expected_prefix_part",
        [
            ("BE", "[BE]"),
            ("FE", "[FE]"),
            ("QA", "[QA]"),
            ("DevOps", "[DevOps]"),
        ],
    )
    def test_should_handle_various_prefixes(
        self, mock_datetime, use_case, prefix, expected_prefix_part
    ):
        # Given: 다양한 팀 접두사가 주어졌을 때
        mock_datetime.now.return_value = datetime(2026, 1, 27)
        config = ReportConfig(
            space_key="MAI",
            team_name="Team",
            team_prefix=prefix,
            mention_users="",
        )

        # When: 제목을 생성하면
        result = use_case._build_title(config)

        # Then: 해당 접두사가 포함된다
        assert result.startswith(expected_prefix_part)
