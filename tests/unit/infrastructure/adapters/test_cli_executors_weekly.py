"""CLI 실행기 weekly_report 커맨드 테스트 — Claude는 SDK mock, Gemini는 subprocess mock."""

from unittest.mock import MagicMock, patch

from claude_agent_sdk import AssistantMessage, TextBlock

from src.infrastructure.adapters.cli_executors import (
    ClaudeCLIExecutor,
    GeminiCLIExecutor,
)


def _make_fake_query(captured: dict):
    """query mock — 호출 인자를 captured에 저장, 빈 응답 yield."""

    async def fake(**kwargs):
        captured.update(kwargs)
        yield AssistantMessage(content=[TextBlock(text="")], model="claude-sonnet-4-6")

    return fake


class TestClaudeCLIExecutorWeeklyCommand:
    """Claude SDK 실행기 weekly_report 커맨드."""

    def test_should_build_weekly_command_without_mention_users(self):
        # Given: command='weekly_report'
        captured: dict = {}
        executor = ClaudeCLIExecutor(command="weekly_report")
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query(captured),
        ):
            # When
            executor.execute("MAI")
        # Then: prompt가 /weekly_report로 시작
        assert captured["prompt"] == "/weekly_report MAI"

    def test_should_build_weekly_command_with_mention_users(self):
        # Given
        captured: dict = {}
        executor = ClaudeCLIExecutor(command="weekly_report")
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query(captured),
        ):
            # When
            executor.execute("MAI", "@홍길동 @김철수")
        # Then
        assert captured["prompt"] == '/weekly_report MAI "@홍길동 @김철수"'

    def test_should_default_to_daily_report_command(self):
        # Given/When: 기본 생성자
        executor = ClaudeCLIExecutor()
        # Then
        assert executor._command == "daily_report"


class TestGeminiCLIExecutorWeeklyCommand:
    """Gemini CLI 실행기 weekly_report 커맨드 (subprocess 유지)."""

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_weekly_command_without_mention_users(self, mock_popen):
        # Given
        executor = GeminiCLIExecutor(command="weekly_report")
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        # When
        executor.execute("MAI")
        # Then
        expected_command = ["gemini", "-p", "/weekly_report MAI"]
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_weekly_command_with_mention_users(self, mock_popen):
        # Given
        executor = GeminiCLIExecutor(command="weekly_report")
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        # When
        executor.execute("MAI", "@홍길동")
        # Then
        expected_command = ["gemini", "-p", '/weekly_report MAI "@홍길동"']
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    def test_should_default_to_daily_report_command(self):
        # Given/When
        executor = GeminiCLIExecutor()
        # Then
        assert executor._command == "daily_report"
