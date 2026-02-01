"""main.py weekly mode 통합 테스트"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.adapters.cli_executors import ClaudeCLIExecutor, GeminiCLIExecutor
from src.infrastructure.config import AppConfig
from src.domain.models import ReportConfig
from src.main import main


class TestMainWeeklyMode:
    """main 함수 weekly mode 통합 테스트"""

    @pytest.fixture
    def weekly_config(self, sample_report_config):
        """weekly mode AppConfig"""
        return AppConfig(
            report=sample_report_config,
            slack_token="test-token",
            slack_channel="test-channel",
            cli_type="claude",
            report_mode="weekly",
        )

    @patch("src.main.GenerateWeeklySummaryUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.load_config_from_env")
    def test_should_use_weekly_summary_use_case_when_weekly_mode(
        self,
        mock_load_config,
        mock_report_generator,
        mock_slack_adapter,
        mock_weekly_use_case_class,
        weekly_config,
    ):
        # Given: report_mode가 "weekly"인 설정
        mock_load_config.return_value = weekly_config
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = True
        mock_weekly_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()

        # Then: GenerateWeeklySummaryUseCase가 사용된다
        mock_weekly_use_case_class.assert_called_once()
        mock_use_case.execute.assert_called_once_with(weekly_config.report)

    @patch("src.main.GenerateWeeklySummaryUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.load_config_from_env")
    def test_should_create_cli_executor_with_weekly_report_command(
        self,
        mock_load_config,
        mock_report_generator,
        mock_slack_adapter,
        mock_weekly_use_case_class,
        weekly_config,
    ):
        # Given: report_mode가 "weekly"인 설정
        mock_load_config.return_value = weekly_config
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = True
        mock_weekly_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()

        # Then: ReportGenerator가 weekly_report 커맨드로 생성된 executor를 받는다
        call_args = mock_report_generator.call_args[0][0]
        assert isinstance(call_args, ClaudeCLIExecutor)
        assert call_args._command == "weekly_report"

    @patch("src.main.GenerateWeeklySummaryUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.load_config_from_env")
    def test_should_use_gemini_executor_in_weekly_mode(
        self,
        mock_load_config,
        mock_report_generator,
        mock_slack_adapter,
        mock_weekly_use_case_class,
        sample_report_config,
    ):
        # Given: weekly mode + gemini CLI 설정
        config = AppConfig(
            report=sample_report_config,
            slack_token="test-token",
            slack_channel="test-channel",
            cli_type="gemini",
            report_mode="weekly",
        )
        mock_load_config.return_value = config
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = True
        mock_weekly_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()

        # Then: GeminiCLIExecutor가 weekly_report 커맨드로 생성된다
        call_args = mock_report_generator.call_args[0][0]
        assert isinstance(call_args, GeminiCLIExecutor)
        assert call_args._command == "weekly_report"

    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.load_config_from_env")
    def test_should_raise_error_for_unknown_cli_type_in_weekly_mode(
        self,
        mock_load_config,
        mock_report_generator,
        mock_slack_adapter,
        sample_report_config,
    ):
        # Given: weekly mode + 알 수 없는 CLI 타입
        config = AppConfig(
            report=sample_report_config,
            slack_token="test-token",
            slack_channel="test-channel",
            cli_type="unknown",
            report_mode="weekly",
        )
        mock_load_config.return_value = config

        # When/Then: main을 호출하면 ValueError가 발생한다
        with pytest.raises(ValueError, match="Unknown CLI type"):
            main()

    @patch("src.main.GenerateWeeklySummaryUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.load_config_from_env")
    def test_should_handle_weekly_use_case_failure(
        self,
        mock_load_config,
        mock_report_generator,
        mock_slack_adapter,
        mock_weekly_use_case_class,
        weekly_config,
    ):
        # Given: weekly 유스케이스가 실패하는 상황
        mock_load_config.return_value = weekly_config
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = False
        mock_weekly_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()  # 예외 없이 종료

        # Then: 유스케이스가 호출되었다
        mock_use_case.execute.assert_called_once()

    @patch("src.main.GenerateWeeklyReportUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.create_cli_executor")
    @patch("src.main.load_config_from_env")
    def test_should_use_daily_use_case_when_daily_mode(
        self,
        mock_load_config,
        mock_create_executor,
        mock_report_generator,
        mock_slack_adapter,
        mock_daily_use_case_class,
        sample_report_config,
    ):
        # Given: report_mode가 "daily" (기본값)인 설정
        config = AppConfig(
            report=sample_report_config,
            slack_token="test-token",
            slack_channel="test-channel",
            cli_type="claude",
            report_mode="daily",
        )
        mock_load_config.return_value = config
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = True
        mock_daily_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()

        # Then: 기존 GenerateWeeklyReportUseCase (daily)가 사용된다
        mock_daily_use_case_class.assert_called_once()
        mock_create_executor.assert_called_once_with("claude")

    @patch.dict(
        os.environ,
        {
            "CONFLUENCE_SPACE_KEY": "MAI",
            "REPORT_MODE": "weekly",
        },
        clear=True,
    )
    @patch("src.main.GenerateWeeklySummaryUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_use_weekly_mode_from_env_variable(
        self,
        mock_load_dotenv,
        mock_report_generator,
        mock_slack_adapter,
        mock_weekly_use_case_class,
    ):
        # Given: REPORT_MODE=weekly 환경변수가 설정된 상황
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = True
        mock_weekly_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()

        # Then: GenerateWeeklySummaryUseCase가 사용된다
        mock_weekly_use_case_class.assert_called_once()
