"""main.py 통합 테스트"""

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.domain.models import ReportConfig
from src.infrastructure.adapters.cli_executors import (
    ClaudeCLIExecutor,
    GeminiCLIExecutor,
)
from src.main import create_cli_executor, main, parse_args


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

    @patch("sys.argv", ["src.main"])
    @patch("src.main.load_config_from_env")
    def test_should_exit_when_config_load_fails(self, mock_load_config):
        # Given: 설정 로드가 실패하는 상황
        mock_load_config.return_value = None

        # When: main을 호출하면
        main()

        # Then: 설정 로드 후 바로 종료 (다른 호출 없음)
        mock_load_config.assert_called_once_with(report_date=None)

    @patch("sys.argv", ["src.main"])
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

    @patch("sys.argv", ["src.main"])
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

    @patch("sys.argv", ["src.main"])
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

    @patch("sys.argv", ["src.main"])
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

    @patch("sys.argv", ["src.main", "--date", "2026-04-06"])
    @patch("src.main.SlackAdapter")
    @patch("src.main.ReportGenerator")
    @patch("src.main.create_cli_executor")
    @patch("src.main.load_config_from_env")
    def test_should_pass_date_argument_to_config(
        self,
        mock_load_config,
        mock_create_executor,
        mock_report_generator,
        mock_slack_adapter,
        sample_report_config,
    ):
        # Given: --date 인자가 주어진 상황
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

        # Then: load_config_from_env에 report_date가 전달된다
        mock_load_config.assert_called_once_with(report_date=date(2026, 4, 6))


class TestParseArgs:
    """CLI 인자 파싱 테스트"""

    @patch("sys.argv", ["src.main"])
    def test_should_default_date_to_none(self):
        # Given: --date 인자가 없는 상황

        # When: parse_args를 호출하면
        args = parse_args()

        # Then: date는 None이다
        assert args.date is None

    @patch("sys.argv", ["src.main", "--date", "2026-04-06"])
    def test_should_parse_date_argument(self):
        # Given: --date 인자가 있는 상황

        # When: parse_args를 호출하면
        args = parse_args()

        # Then: date가 파싱된다
        assert args.date == date(2026, 4, 6)

    @patch("sys.argv", ["src.main", "--date", "invalid"])
    def test_should_raise_error_for_invalid_date_format(self):
        # Given: 잘못된 날짜 형식

        # When/Then: parse_args를 호출하면 SystemExit이 발생한다
        with pytest.raises(SystemExit):
            parse_args()


class TestMainCreatePage:
    """main 함수 create_page 모드 테스트"""

    @patch("sys.argv", ["src.main"])
    @patch("src.main.ClaudeCLIExecutor")
    @patch("src.main.load_config_from_env")
    def test_should_create_page_with_correct_command(
        self,
        mock_load_config,
        mock_claude_executor_class,
    ):
        # Given: report_mode가 create_page인 상황
        from src.infrastructure.config import AppConfig

        mock_config = AppConfig(
            report=ReportConfig(
                space_key="MAI",
                team_name="",
                team_prefix="BE",
                mention_users="",
            ),
            slack_token="",
            slack_channel="",
            cli_type="claude",
            report_mode="create_page",
            parent_page_id="1477279756",
            team_members=["홍길동", "김철수"],
        )
        mock_load_config.return_value = mock_config
        mock_executor = MagicMock()
        mock_executor.execute.return_value = "Page created"
        mock_claude_executor_class.return_value = mock_executor

        # When: main을 호출하면
        main()

        # Then: create_weekly_page 명령으로 CLIExecutor가 생성된다
        mock_claude_executor_class.assert_called_once_with(command="create_weekly_page")
        # And: execute가 space_key와 parent_page_id+team_members로 호출된다
        mock_executor.execute.assert_called_once()
        call_args = mock_executor.execute.call_args
        assert call_args[0][0] == "MAI"
        assert "1477279756" in call_args[0][1]
        assert "홍길동" in call_args[0][1]
        assert "김철수" in call_args[0][1]

    @patch("sys.argv", ["src.main"])
    @patch("src.main.ClaudeCLIExecutor")
    @patch("src.main.load_config_from_env")
    def test_should_handle_create_page_failure(
        self,
        mock_load_config,
        mock_claude_executor_class,
    ):
        # Given: CLI 실행이 실패하는 상황
        from src.infrastructure.config import AppConfig

        mock_config = AppConfig(
            report=ReportConfig(
                space_key="MAI",
                team_name="",
                team_prefix="",
                mention_users="",
            ),
            slack_token="",
            slack_channel="",
            cli_type="claude",
            report_mode="create_page",
            parent_page_id="123",
            team_members=["홍길동"],
        )
        mock_load_config.return_value = mock_config
        mock_executor = MagicMock()
        mock_executor.execute.return_value = None
        mock_claude_executor_class.return_value = mock_executor

        # When: main을 호출하면
        main()  # 예외 없이 종료

        # Then: execute가 호출되었다
        mock_executor.execute.assert_called_once()
