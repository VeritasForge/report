"""main.py 단위 테스트 — argparse + 우선순위 병합 (plan Task 2).

카테고리: [Happy] / [Boundary] / [Error] — CLAUDE.md Test Coverage Categories.
"""

import dataclasses
import sys
from dataclasses import dataclass
from datetime import date
from unittest.mock import patch

import pytest

from src.application.use_cases import GenerateReportUseCase
from src.domain.models import ReportConfig
from src.infrastructure.adapters.cli_executors import ClaudeCLIExecutor
from src.infrastructure.adapters.slack_adapter import SlackAdapter
from src.infrastructure.adapters.stdout_adapter import StdoutAdapter
from src.infrastructure.config import AppConfig
from src.main import (
    build_report_use_case,
    create_cli_executor,
    create_notifier,
    parse_args,
    resolve_effective_settings,
    run_create_page_mode,
)


@pytest.fixture
def daily_config() -> AppConfig:
    return AppConfig(
        report=ReportConfig(
            space_key="MAI", team_name="Backend Team",
            team_prefix="BE", mention_users="", report_date=None,
        ),
        slack_token="test-token",
        slack_channel="C-daily",
        slack_channel_weekly="C-weekly",
        cli_type="claude",
        report_mode="daily",
    )


@pytest.fixture
def weekly_config(daily_config) -> AppConfig:
    return dataclasses.replace(daily_config, report_mode="weekly")


@pytest.fixture
def daily_config_unknown_cli(daily_config) -> AppConfig:
    return dataclasses.replace(daily_config, cli_type="unknown")


@dataclass
class _StubConfig:
    cli_model: str | None = None
    dry_run: bool = False


@dataclass
class _StubArgs:
    model: str | None = None
    dry_run: bool = False


class TestParseArgs:
    """argparse가 새 옵션을 인식한다."""

    # ---------- [Happy] ----------
    def test_should_parse_model_flag(self):
        # Given: --model sonnet
        with patch.object(sys, "argv", ["main.py", "--model", "sonnet"]):
            # When
            args = parse_args()
        # Then
        assert args.model == "sonnet"

    def test_should_parse_dry_run_flag(self):
        # Given: --dry-run
        with patch.object(sys, "argv", ["main.py", "--dry-run"]):
            # When
            args = parse_args()
        # Then
        assert args.dry_run is True

    # ---------- [Boundary] ----------
    def test_should_default_model_to_none_when_flag_missing(self):
        # Given: no --model
        with patch.object(sys, "argv", ["main.py"]):
            # When
            args = parse_args()
        # Then
        assert args.model is None

    def test_should_default_dry_run_to_false_when_flag_missing(self):
        # Given: no --dry-run
        with patch.object(sys, "argv", ["main.py"]):
            # When
            args = parse_args()
        # Then
        assert args.dry_run is False

    # ---------- [Error] ----------
    def test_should_exit_with_argparse_error_when_model_flag_has_no_value(self):
        # Given: --model 뒤 값 없음
        with patch.object(sys, "argv", ["main.py", "--model"]):
            # When/Then: argparse가 SystemExit 발생
            with pytest.raises(SystemExit):
                parse_args()


class TestResolveEffectiveSettings:
    """args(CLI) + config(ENV) 우선순위 병합."""

    # ---------- [Happy] — CLI 우선 ----------
    def test_should_prefer_cli_model_over_env_when_both_set(self):
        # Given: CLI=sonnet, ENV=haiku
        args = _StubArgs(model="sonnet")
        config = _StubConfig(cli_model="haiku")
        # When
        model, _ = resolve_effective_settings(args, config)
        # Then: CLI 채택
        assert model == "sonnet"

    def test_should_prefer_cli_dry_run_over_env_when_both_set(self):
        # Given: CLI=True, ENV=False (CLI 명시 우선)
        args = _StubArgs(dry_run=True)
        config = _StubConfig(dry_run=False)
        # When
        _, dry_run = resolve_effective_settings(args, config)
        # Then
        assert dry_run is True

    # ---------- [Boundary] — fallback ----------
    def test_should_fall_back_to_env_model_when_cli_arg_missing(self):
        # Given: CLI 미지정, ENV=haiku
        args = _StubArgs()
        config = _StubConfig(cli_model="haiku")
        # When
        model, _ = resolve_effective_settings(args, config)
        # Then
        assert model == "haiku"

    def test_should_fall_back_to_env_dry_run_when_cli_flag_missing(self):
        # Given: CLI 미지정, ENV=True
        args = _StubArgs(dry_run=False)
        config = _StubConfig(dry_run=True)
        # When
        _, dry_run = resolve_effective_settings(args, config)
        # Then
        assert dry_run is True

    def test_should_default_to_sonnet_when_neither_cli_nor_env_set(self):
        # Given: 둘 다 없음
        args = _StubArgs()
        config = _StubConfig()
        # When
        model, _ = resolve_effective_settings(args, config)
        # Then: 코드 default "sonnet"
        assert model == "sonnet"

    def test_should_default_dry_run_to_false_when_neither_set(self):
        # Given: 둘 다 없음
        args = _StubArgs()
        config = _StubConfig()
        # When
        _, dry_run = resolve_effective_settings(args, config)
        # Then
        assert dry_run is False


class TestCreateNotifier:
    """dry_run 분기로 StdoutAdapter / SlackAdapter 주입 — plan Task 4.

    [Error] 부재 사유: `create_notifier`는 외부 IO 없는 순수 팩토리 함수.
    SlackAdapter는 send 시점에 token 누락을 warning으로 처리하므로 init 단계 예외 없음.
    """

    # ---------- [Happy] ----------
    def test_should_return_stdout_adapter_when_dry_run_true(self):
        # Given: dry_run=True
        # When
        notifier = create_notifier(dry_run=True, slack_token="x", slack_channel="C1")
        # Then
        assert isinstance(notifier, StdoutAdapter)

    def test_should_return_slack_adapter_when_dry_run_false(self):
        # Given: dry_run=False
        # When
        notifier = create_notifier(dry_run=False, slack_token="x", slack_channel="C1")
        # Then
        assert isinstance(notifier, SlackAdapter)

    def test_should_return_slack_adapter_with_correct_channel_for_daily(self):
        # Given: daily channel
        # When
        notifier = create_notifier(dry_run=False, slack_token="t", slack_channel="C-daily")
        # Then: SlackAdapter가 채널을 정확히 받음
        assert isinstance(notifier, SlackAdapter)
        assert notifier._channel == "C-daily"

    def test_should_return_slack_adapter_with_correct_channel_for_weekly(self):
        # Given: weekly channel (같은 팩토리가 채널만 다르게)
        # When
        notifier = create_notifier(dry_run=False, slack_token="t", slack_channel="C-weekly")
        # Then
        assert isinstance(notifier, SlackAdapter)
        assert notifier._channel == "C-weekly"

    # ---------- [Boundary] ----------
    def test_should_return_stdout_adapter_even_when_slack_token_missing(self):
        # Given: dry_run=True + SLACK_TOKEN 빈 문자열
        # When
        notifier = create_notifier(dry_run=True, slack_token="", slack_channel="")
        # Then: dry_run이 우선이므로 StdoutAdapter (Slack init 시도 안 함)
        assert isinstance(notifier, StdoutAdapter)

    def test_should_return_slack_adapter_with_empty_token_when_dry_run_false(self):
        # Given: dry_run=False + token 빈 (production 미설정 시나리오)
        # When
        notifier = create_notifier(dry_run=False, slack_token="", slack_channel="")
        # Then: SlackAdapter 인스턴스화는 성공 (send 시점에 warning)
        assert isinstance(notifier, SlackAdapter)


class TestCreateCliExecutor:
    """cli_type → 적절한 Executor 팩토리."""

    # ---------- [Happy] ----------
    def test_should_return_claude_executor_when_cli_type_is_claude(self):
        # Given/When
        executor = create_cli_executor("claude")
        # Then
        assert isinstance(executor, ClaudeCLIExecutor)

    def test_should_pass_command_and_model_to_claude_executor(self):
        # Given/When: 명시적 command + model 전달
        executor = create_cli_executor("claude", command="weekly_report", model="haiku")
        # Then: Claude executor가 두 값을 보관
        assert isinstance(executor, ClaudeCLIExecutor)
        assert executor._command == "weekly_report"
        assert executor._model == "haiku"

    # ---------- [Error] ----------
    def test_should_raise_value_error_when_cli_type_is_gemini(self):
        # Given: gemini 실행기는 제거됨
        # When/Then: gemini 요청 시 ValueError 발생
        with pytest.raises(ValueError) as exc_info:
            create_cli_executor("gemini")
        assert "Unknown CLI type: gemini" in str(exc_info.value)

    def test_should_raise_value_error_for_unknown_cli_type(self):
        # Given/When/Then
        with pytest.raises(ValueError, match="Unknown CLI type"):
            create_cli_executor("unknown")


class TestBuildReportUseCase:
    """report_mode → use case 조립 팩토리 — plan Task 4."""

    # ---------- [Happy] ----------
    def test_should_build_daily_use_case_with_daily_channel(self, daily_config):
        # [Happy] Given: report_mode=daily 설정
        # When
        use_case = build_report_use_case(daily_config, model="sonnet", dry_run=False)
        # Then: Daily 접미사 + SlackAdapter(daily 채널)
        assert isinstance(use_case, GenerateReportUseCase)
        assert use_case._title_suffix == "Daily"
        assert isinstance(use_case._notifier, SlackAdapter)

    def test_should_build_weekly_use_case_with_weekly_channel(self, weekly_config):
        # [Happy] Given: report_mode=weekly 설정
        # When
        use_case = build_report_use_case(weekly_config, model="sonnet", dry_run=False)
        # Then: Weekly 접미사
        assert use_case._title_suffix == "Weekly"

    # ---------- [Boundary] ----------
    def test_should_use_stdout_adapter_when_dry_run(self, daily_config):
        # [Boundary] Given: dry_run=True
        use_case = build_report_use_case(daily_config, model="sonnet", dry_run=True)
        # Then: StdoutAdapter 주입 (Slack 미호출 경로)
        assert isinstance(use_case._notifier, StdoutAdapter)

    # ---------- [Error] ----------
    def test_should_raise_for_unknown_cli_type(self, daily_config_unknown_cli):
        # [Error] Given: 알 수 없는 CLI_TYPE
        with pytest.raises(ValueError):
            build_report_use_case(daily_config_unknown_cli, model="sonnet", dry_run=False)


class TestRunCreatePageMode:
    """create_page 모드 함수 — SlackAdapter truthy arm 커버 (plan Task 4).

    [Error] 부재 사유: ENV 가드 실패(False 반환)는 [Boundary]로 커버,
    외부 예외는 CreateWeeklyPageUseCase 내부 정책 (해당 use case 테스트 영역).
    """

    # ---------- [Happy] ----------
    def test_should_wire_slack_notifier_when_channel_and_token_set(self, daily_config):
        # [Happy] Given: create_page 모드 + Slack 채널/토큰 설정
        config = dataclasses.replace(
            daily_config,
            report_mode="create_page",
            confluence_url="https://x.atlassian.net",
            confluence_user="u",
            confluence_token="t",
            parent_page_id="123",
            slack_channel_create_page="C-page",
        )
        with (
            patch("src.main.SlackAdapter") as mock_slack,
            patch("src.infrastructure.adapters.confluence_adapter.ConfluenceAdapter"),
            patch("src.application.create_page_use_case.CreateWeeklyPageUseCase") as mock_uc,
        ):
            mock_uc.return_value.execute.return_value = True
            # When
            result = run_create_page_mode(config, date(2026, 6, 8))
        # Then: SlackAdapter가 create_page 전용 채널로 생성된다
        assert result is True
        mock_slack.assert_called_once_with(token="test-token", channel="C-page")

    # ---------- [Boundary] ----------
    def test_should_return_false_when_confluence_env_missing(self, daily_config, capsys):
        # [Boundary] Given: create_page 모드인데 Confluence ENV 미설정 (빈 문자열)
        config = dataclasses.replace(daily_config, report_mode="create_page")
        # When
        result = run_create_page_mode(config, date(2026, 6, 8))
        # Then: 가드 에러 출력 후 False 반환
        assert result is False
        captured = capsys.readouterr()
        assert "CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN" in captured.out

    def test_should_skip_slack_notifier_when_channel_not_set(self, daily_config):
        # [Boundary] Given: create_page 채널 미설정 (notifier=None arm)
        config = dataclasses.replace(
            daily_config,
            report_mode="create_page",
            confluence_url="https://x.atlassian.net",
            confluence_user="u",
            confluence_token="t",
            parent_page_id="123",
            slack_channel_create_page="",
        )
        with (
            patch("src.main.SlackAdapter") as mock_slack,
            patch("src.infrastructure.adapters.confluence_adapter.ConfluenceAdapter"),
            patch("src.application.create_page_use_case.CreateWeeklyPageUseCase") as mock_uc,
        ):
            mock_uc.return_value.execute.return_value = False
            # When
            result = run_create_page_mode(config, date(2026, 6, 8))
        # Then: SlackAdapter 미생성 + use case 실패가 그대로 반환된다
        assert result is False
        mock_slack.assert_not_called()
        assert mock_uc.call_args.kwargs["notifier"] is None
