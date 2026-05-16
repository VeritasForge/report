"""main.py 통합 테스트"""

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

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

        # Then: 의존성이 올바르게 생성된다 (Task 2/5: model 파라미터 default sonnet 전달)
        mock_create_executor.assert_called_once_with("claude", model="sonnet")
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

        # Then: gemini 실행기가 생성된다 (Task 5: model은 Gemini에서 무시되지만 인자는 전달)
        mock_create_executor.assert_called_once_with("gemini", model="sonnet")

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


class TestMainCreatePageMode:
    """create_page 모드 통합 테스트"""

    @patch("sys.argv", ["src.main"])
    @patch("src.main.load_config_from_env")
    def test_should_exit_when_confluence_credentials_missing(self, mock_load_config):
        # Given: create_page 모드이지만 Confluence 인증 정보가 없는 상황
        from src.infrastructure.config import AppConfig
        from src.domain.models import ReportConfig

        mock_config = AppConfig(
            report=ReportConfig(space_key="MAI", team_name="", team_prefix="", mention_users=""),
            slack_token="",
            slack_channel="",
            cli_type="claude",
            report_mode="create_page",
            confluence_url="",
            confluence_user="",
            confluence_token="",
        )
        mock_load_config.return_value = mock_config

        # When: main을 호출하면
        main()

        # Then: 설정 로드 후 인증 오류로 종료 (use_case 실행 없음)
        mock_load_config.assert_called_once()

    @patch("sys.argv", ["src.main"])
    @patch("src.main.load_config_from_env")
    def test_should_execute_create_page_use_case_when_credentials_present(
        self, mock_load_config
    ):
        # Given: create_page 모드이고 Confluence 인증 정보가 있는 상황
        from src.infrastructure.config import AppConfig
        from src.domain.models import ReportConfig

        mock_config = AppConfig(
            report=ReportConfig(space_key="MAI", team_name="", team_prefix="", mention_users=""),
            slack_token="",
            slack_channel="",
            cli_type="claude",
            report_mode="create_page",
            confluence_url="https://example.atlassian.net",
            confluence_user="user@example.com",
            confluence_token="token123",
            parent_page_id="111222",
        )
        mock_load_config.return_value = mock_config

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = True

        with patch("src.infrastructure.adapters.confluence_adapter.ConfluenceAdapter") as mock_confluence_cls, \
             patch("src.infrastructure.adapters.page_transformer.PageTransformer") as mock_transformer_cls, \
             patch("src.application.create_page_use_case.CreateWeeklyPageUseCase") as mock_use_case_cls:
            mock_use_case_cls.return_value = mock_use_case

            # When: main을 호출하면
            main()

            # Then: ConfluenceAdapter, PageTransformer, CreateWeeklyPageUseCase가 생성되고 실행된다
            mock_confluence_cls.assert_called_once_with(
                url="https://example.atlassian.net",
                user="user@example.com",
                token="token123",
            )
            mock_transformer_cls.assert_called_once()
            mock_use_case.execute.assert_called_once()

    @patch("sys.argv", ["src.main"])
    @patch("src.main.load_config_from_env")
    def test_should_print_error_when_create_page_fails(self, mock_load_config, capsys):
        # Given: create_page 모드이고 실행이 실패하는 상황
        from src.infrastructure.config import AppConfig
        from src.domain.models import ReportConfig

        mock_config = AppConfig(
            report=ReportConfig(space_key="MAI", team_name="", team_prefix="", mention_users=""),
            slack_token="",
            slack_channel="",
            cli_type="claude",
            report_mode="create_page",
            confluence_url="https://example.atlassian.net",
            confluence_user="user@example.com",
            confluence_token="token123",
            parent_page_id="111222",
        )
        mock_load_config.return_value = mock_config

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = False

        with patch("src.infrastructure.adapters.confluence_adapter.ConfluenceAdapter"), \
             patch("src.infrastructure.adapters.page_transformer.PageTransformer"), \
             patch("src.application.create_page_use_case.CreateWeeklyPageUseCase") as mock_use_case_cls:
            mock_use_case_cls.return_value = mock_use_case

            # When: main을 호출하면
            main()

            # Then: 에러 메시지가 출력된다
            captured = capsys.readouterr()
            assert "ERROR: Failed to create weekly page." in captured.out


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
