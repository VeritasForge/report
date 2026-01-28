"""main.py 통합 테스트"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.adapters.cli_executors import (
    ClaudeCLIExecutor,
    GeminiCLIExecutor,
)
from src.main import create_cli_executor, main


class TestCreateCliExecutor:
    """CLI 실행기 팩토리 테스트"""

    def test_should_create_claude_executor(self):
        # Given: cli_type이 "claude"인 경우

        # When: create_cli_executor를 호출하면
        executor = create_cli_executor("claude")

        # Then: ClaudeCLIExecutor 인스턴스를 반환한다
        assert isinstance(executor, ClaudeCLIExecutor)

    def test_should_create_gemini_executor(self):
        # Given: cli_type이 "gemini"인 경우

        # When: create_cli_executor를 호출하면
        executor = create_cli_executor("gemini")

        # Then: GeminiCLIExecutor 인스턴스를 반환한다
        assert isinstance(executor, GeminiCLIExecutor)

    def test_should_raise_error_for_unknown_cli_type(self):
        # Given: 알 수 없는 cli_type

        # When/Then: create_cli_executor를 호출하면 ValueError가 발생한다
        with pytest.raises(ValueError, match="Unknown CLI type"):
            create_cli_executor("unknown")

    def test_should_include_supported_types_in_error_message(self):
        # Given: 알 수 없는 cli_type

        # When/Then: 에러 메시지에 지원되는 타입이 포함된다
        with pytest.raises(ValueError) as exc_info:
            create_cli_executor("invalid")

        assert "claude" in str(exc_info.value)
        assert "gemini" in str(exc_info.value)


class TestMain:
    """main 함수 통합 테스트"""

    @patch("src.main.load_config_from_env")
    def test_should_exit_when_config_load_fails(self, mock_load_config):
        # Given: 설정 로드가 실패하는 상황
        mock_load_config.return_value = None

        # When: main을 호출하면
        main()

        # Then: 설정 로드 후 바로 종료 (다른 호출 없음)
        mock_load_config.assert_called_once()

    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.create_cli_executor")
    @patch("src.main.load_config_from_env")
    def test_should_create_dependencies_correctly(
        self,
        mock_load_config,
        mock_create_executor,
        mock_report_generator,
        mock_slack_adapter,
        sample_report_config,
    ):
        # Given: 설정이 올바르게 로드되는 상황
        from src.infrastructure.config import AppConfig

        mock_config = AppConfig(
            report=sample_report_config,
            slack_token="test-token",
            slack_channel="test-channel",
            cli_type="claude",
        )
        mock_load_config.return_value = mock_config
        mock_executor = MagicMock()
        mock_create_executor.return_value = mock_executor
        mock_generator = MagicMock()
        mock_generator.generate.return_value = None
        mock_report_generator.return_value = mock_generator

        # When: main을 호출하면
        main()

        # Then: 의존성이 올바르게 생성된다
        mock_create_executor.assert_called_once_with("claude")
        mock_report_generator.assert_called_once_with(mock_executor)
        mock_slack_adapter.assert_called_once_with(
            token="test-token", channel="test-channel"
        )

    @patch("src.main.GenerateWeeklyReportUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.create_cli_executor")
    @patch("src.main.load_config_from_env")
    def test_should_execute_use_case(
        self,
        mock_load_config,
        mock_create_executor,
        mock_report_generator,
        mock_slack_adapter,
        mock_use_case_class,
        sample_report_config,
    ):
        # Given: 모든 의존성이 준비된 상황
        from src.infrastructure.config import AppConfig

        mock_config = AppConfig(
            report=sample_report_config,
            slack_token="test-token",
            slack_channel="test-channel",
            cli_type="claude",
        )
        mock_load_config.return_value = mock_config
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = True
        mock_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()

        # Then: 유스케이스가 실행된다
        mock_use_case.execute.assert_called_once_with(sample_report_config)

    @patch("src.main.GenerateWeeklyReportUseCase")
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.create_cli_executor")
    @patch("src.main.load_config_from_env")
    def test_should_handle_use_case_failure(
        self,
        mock_load_config,
        mock_create_executor,
        mock_report_generator,
        mock_slack_adapter,
        mock_use_case_class,
        sample_report_config,
    ):
        # Given: 유스케이스가 실패하는 상황
        from src.infrastructure.config import AppConfig

        mock_config = AppConfig(
            report=sample_report_config,
            slack_token="test-token",
            slack_channel="test-channel",
            cli_type="claude",
        )
        mock_load_config.return_value = mock_config
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = False
        mock_use_case_class.return_value = mock_use_case

        # When: main을 호출하면
        main()  # 예외 없이 종료

        # Then: 유스케이스가 호출되었다
        mock_use_case.execute.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "CONFLUENCE_SPACE_KEY": "MAI",
            "CLI_TYPE": "gemini",
        },
        clear=True,
    )
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.create_cli_executor")
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_use_gemini_when_configured(
        self,
        mock_load_dotenv,
        mock_create_executor,
        mock_report_generator,
        mock_slack_adapter,
    ):
        # Given: CLI_TYPE이 gemini로 설정된 상황
        mock_executor = MagicMock()
        mock_create_executor.return_value = mock_executor
        mock_generator = MagicMock()
        mock_generator.generate.return_value = None
        mock_report_generator.return_value = mock_generator

        # When: main을 호출하면
        main()

        # Then: gemini 실행기가 생성된다
        mock_create_executor.assert_called_once_with("gemini")
