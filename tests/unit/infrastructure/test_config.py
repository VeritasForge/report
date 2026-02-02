"""Infrastructure 설정 로더 테스트"""

import os
from unittest.mock import patch

import pytest

from src.infrastructure.config import AppConfig, load_config_from_env


class TestLoadConfigFromEnv:
    """환경변수에서 설정 로드 테스트"""

    @patch.dict(
        os.environ,
        {
            "CONFLUENCE_SPACE_KEY": "MAI",
            "REPORT_TEAM_NAME": "Backend Team",
            "REPORT_TEAM_PREFIX": "BE",
            "REPORT_MENTION_USERS": "@홍길동 @김철수",
            "SLACK_TOKEN": "xoxb-test-token",
            "SLACK_CHANNEL": "C12345678",
            "SLACK_CHANNEL_WEEKLY": "C99999999",
            "CLI_TYPE": "claude",
        },
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_load_all_config_values(self, mock_load_dotenv):
        # Given: 모든 환경변수가 설정된 상황

        # When: 설정을 로드하면
        config = load_config_from_env()

        # Then: 모든 값이 올바르게 로드된다
        assert config is not None
        assert config.report.space_key == "MAI"
        assert config.report.team_name == "Backend Team"
        assert config.report.team_prefix == "BE"
        assert config.report.mention_users == "@홍길동 @김철수"
        assert config.slack_token == "xoxb-test-token"
        assert config.slack_channel == "C12345678"
        assert config.slack_channel_weekly == "C99999999"
        assert config.cli_type == "claude"

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_return_none_when_space_key_missing(self, mock_load_dotenv):
        # Given: CONFLUENCE_SPACE_KEY가 없는 상황

        # When: 설정을 로드하면
        config = load_config_from_env()

        # Then: None을 반환한다
        assert config is None

    @patch.dict(
        os.environ,
        {"CONFLUENCE_SPACE_KEY": "MAI"},
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_use_default_values_for_optional_fields(self, mock_load_dotenv):
        # Given: 필수 값만 설정된 상황

        # When: 설정을 로드하면
        config = load_config_from_env()

        # Then: 선택적 필드는 기본값이 사용된다
        assert config is not None
        assert config.report.team_name == ""
        assert config.report.team_prefix == ""
        assert config.report.mention_users == ""
        assert config.slack_token == ""
        assert config.slack_channel == ""
        assert config.slack_channel_weekly == ""
        assert config.cli_type == "claude"

    @patch.dict(
        os.environ,
        {
            "CONFLUENCE_SPACE_KEY": "MAI",
            "CLI_TYPE": "gemini",
        },
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_load_gemini_cli_type(self, mock_load_dotenv):
        # Given: CLI_TYPE이 gemini로 설정된 상황

        # When: 설정을 로드하면
        config = load_config_from_env()

        # Then: cli_type이 gemini로 설정된다
        assert config is not None
        assert config.cli_type == "gemini"

    @patch.dict(
        os.environ,
        {
            "CONFLUENCE_SPACE_KEY": "TEST",
        },
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_call_load_dotenv(self, mock_load_dotenv):
        # Given: 환경변수가 설정된 상황

        # When: 설정을 로드하면
        load_config_from_env()

        # Then: load_dotenv가 호출된다
        mock_load_dotenv.assert_called_once()


class TestAppConfig:
    """AppConfig 데이터클래스 테스트"""

    def test_should_create_app_config_with_all_fields(self, sample_report_config):
        # Given: 모든 필드가 주어졌을 때
        # When: AppConfig를 생성하면
        config = AppConfig(
            report=sample_report_config,
            slack_token="xoxb-test-token",
            slack_channel="C12345678",
            cli_type="claude",
        )

        # Then: 모든 필드가 올바르게 설정된다
        assert config.report == sample_report_config
        assert config.slack_token == "xoxb-test-token"
        assert config.slack_channel == "C12345678"
        assert config.cli_type == "claude"
