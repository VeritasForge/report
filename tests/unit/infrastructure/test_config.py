"""Infrastructure 설정 로더 테스트"""

import os
from datetime import date
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
        {"CONFLUENCE_SPACE_KEY": "MAI"},
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_pass_report_date_to_config(self, mock_load_dotenv):
        # Given: report_date가 지정된 상황
        target_date = date(2026, 4, 6)

        # When: 설정을 로드하면
        config = load_config_from_env(report_date=target_date)

        # Then: ReportConfig에 report_date가 전달된다
        assert config is not None
        assert config.report.report_date == target_date

    @patch.dict(
        os.environ,
        {"CONFLUENCE_SPACE_KEY": "MAI"},
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_default_report_date_to_none(self, mock_load_dotenv):
        # Given: report_date가 지정되지 않은 상황

        # When: 설정을 로드하면
        config = load_config_from_env()

        # Then: report_date는 None이다
        assert config is not None
        assert config.report.report_date is None

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


class TestLoadConfigFromEnvCreatePage:
    """create_page 모드 설정 로드 테스트"""

    @patch.dict(
        os.environ,
        {
            "CONFLUENCE_SPACE_KEY": "MAI",
            "CONFLUENCE_URL": "https://test.atlassian.net",
            "CONFLUENCE_USER": "test@test.com",
            "CONFLUENCE_TOKEN": "test-token",
            "PARENT_PAGE_ID": "1477279756",
            "REPORT_MODE": "create_page",
        },
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_load_confluence_credentials(self, mock_load_dotenv):
        # Given: Confluence 인증 환경변수가 설정된 상황

        # When: 설정을 로드하면
        config = load_config_from_env()

        # Then: Confluence 인증 정보가 로드된다
        assert config is not None
        assert config.confluence_url == "https://test.atlassian.net"
        assert config.confluence_user == "test@test.com"
        assert config.confluence_token == "test-token"
        assert config.parent_page_id == "1477279756"
        assert config.report_mode == "create_page"

    @patch.dict(
        os.environ,
        {"CONFLUENCE_SPACE_KEY": "MAI"},
        clear=True,
    )
    @patch("src.infrastructure.config.load_dotenv")
    def test_should_default_confluence_fields_to_empty(self, mock_load_dotenv):
        # Given: Confluence 인증 환경변수가 없는 상황

        # When: 설정을 로드하면
        config = load_config_from_env()

        # Then: 기본값은 빈 문자열이다
        assert config is not None
        assert config.confluence_url == ""
        assert config.confluence_user == ""
        assert config.confluence_token == ""
        assert config.parent_page_id == ""


class TestLoadConfigFromEnvCreatePageNotification:
    """SLACK_CHANNEL_CREATE_PAGE env 로딩"""

    @pytest.fixture(autouse=True)
    def _isolate_env_and_dotenv(self, monkeypatch):
        # .env 파일 leak 방지 (load_dotenv mock) + 해당 키 격리
        monkeypatch.setattr("src.infrastructure.config.load_dotenv", lambda: None)
        monkeypatch.delenv("SLACK_CHANNEL_CREATE_PAGE", raising=False)

    def test_should_load_slack_channel_create_page_when_set(self, monkeypatch):
        # Given: env 변수 설정
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("SLACK_CHANNEL_CREATE_PAGE", "C12345CREATE")

        # When: 설정 로드
        from src.infrastructure.config import load_config_from_env
        config = load_config_from_env()

        # Then: slack_channel_create_page 필드에 채워진다
        assert config is not None
        assert config.slack_channel_create_page == "C12345CREATE"

    def test_should_default_slack_channel_create_page_to_empty_when_unset(self, monkeypatch):
        # Given: SLACK_CHANNEL_CREATE_PAGE 미설정
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.delenv("SLACK_CHANNEL_CREATE_PAGE", raising=False)

        # When: 설정 로드
        from src.infrastructure.config import load_config_from_env
        config = load_config_from_env()

        # Then: 빈 문자열 (None 아님 — dataclass default)
        assert config is not None
        assert config.slack_channel_create_page == ""


class TestCliModelAndDryRun:
    """CLI_MODEL / DRY_RUN 환경변수 로딩 — plan Task 1.

    카테고리: [Happy] / [Boundary] / [Error] — CLAUDE.md Test Coverage Categories.
    """

    @pytest.fixture(autouse=True)
    def _isolate_env_and_dotenv(self, monkeypatch):
        # .env 파일 leak 방지 + 본 클래스가 다루는 env 키 격리
        monkeypatch.setattr("src.infrastructure.config.load_dotenv", lambda: None)
        monkeypatch.delenv("CLI_MODEL", raising=False)
        monkeypatch.delenv("DRY_RUN", raising=False)

    # ---------- [Happy] ----------
    def test_should_load_cli_model_from_env_when_set(self, monkeypatch):
        # Given: CLI_MODEL 환경변수가 sonnet으로 설정
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("CLI_MODEL", "sonnet")

        # When: 설정 로드
        config = load_config_from_env()

        # Then: cli_model 필드에 채워진다
        assert config is not None
        assert config.cli_model == "sonnet"

    def test_should_load_dry_run_true_when_env_is_1(self, monkeypatch):
        # Given: DRY_RUN=1
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("DRY_RUN", "1")

        # When: 설정 로드
        config = load_config_from_env()

        # Then: dry_run is True
        assert config is not None
        assert config.dry_run is True

    @pytest.mark.parametrize("value", ["true", "True", "TRUE"])
    def test_should_load_dry_run_true_when_env_is_true_case_insensitive(self, monkeypatch, value):
        # Given: DRY_RUN이 'true'의 대소문자 변종
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("DRY_RUN", value)

        # When: 설정 로드
        config = load_config_from_env()

        # Then: dry_run is True
        assert config is not None
        assert config.dry_run is True

    # ---------- [Boundary] ----------
    def test_should_default_cli_model_to_none_when_unset(self, monkeypatch):
        # Given: CLI_MODEL 미설정
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.delenv("CLI_MODEL", raising=False)

        # When: 설정 로드
        config = load_config_from_env()

        # Then: cli_model is None
        assert config is not None
        assert config.cli_model is None

    def test_should_default_dry_run_to_false_when_unset(self, monkeypatch):
        # Given: DRY_RUN 미설정
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.delenv("DRY_RUN", raising=False)

        # When: 설정 로드
        config = load_config_from_env()

        # Then: dry_run is False
        assert config is not None
        assert config.dry_run is False

    def test_should_treat_empty_cli_model_as_none(self, monkeypatch):
        # Given: CLI_MODEL=""
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("CLI_MODEL", "")

        # When: 설정 로드
        config = load_config_from_env()

        # Then: 빈 문자열은 None으로 정규화
        assert config is not None
        assert config.cli_model is None

    def test_should_treat_dry_run_zero_as_false(self, monkeypatch):
        # Given: DRY_RUN=0 (falsy)
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("DRY_RUN", "0")

        # When: 설정 로드
        config = load_config_from_env()

        # Then: dry_run is False
        assert config is not None
        assert config.dry_run is False

    @pytest.mark.parametrize("value", ["false", "False", "FALSE"])
    def test_should_treat_dry_run_false_string_as_false(self, monkeypatch, value):
        # Given: DRY_RUN이 'false'의 대소문자 변종
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("DRY_RUN", value)

        # When: 설정 로드
        config = load_config_from_env()

        # Then: dry_run is False
        assert config is not None
        assert config.dry_run is False

    # ---------- [Error] ----------
    @pytest.mark.parametrize("value", ["yes", "enabled", "on", "random_string"])
    def test_should_treat_dry_run_arbitrary_string_as_false(self, monkeypatch, value):
        # Given: DRY_RUN이 truthy 화이트리스트(1/true)에 없는 임의 문자열
        # 정책: 안전한 기본값 — 모르는 값은 False (잘못된 dry-run 활성화 회피)
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "MAI")
        monkeypatch.setenv("DRY_RUN", value)

        # When: 설정 로드
        config = load_config_from_env()

        # Then: dry_run is False (안전 기본)
        assert config is not None
        assert config.dry_run is False
