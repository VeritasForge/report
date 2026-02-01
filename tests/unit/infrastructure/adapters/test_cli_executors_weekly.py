"""CLI 실행기 weekly_report 커맨드 테스트"""

from unittest.mock import MagicMock, patch

from src.infrastructure.adapters.cli_executors import (
    ClaudeCLIExecutor,
    GeminiCLIExecutor,
)


class TestClaudeCLIExecutorWeeklyCommand:
    """Claude CLI 실행기 weekly_report 커맨드 테스트"""

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_weekly_command_without_mention_users(self, mock_popen):
        # Given: weekly_report 커맨드로 생성된 실행기
        executor = ClaudeCLIExecutor(command="weekly_report")
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        executor.execute("MAI")

        # Then: /weekly_report 커맨드가 실행된다
        expected_command = [
            "claude",
            "-p",
            "/weekly_report MAI",
            "--dangerously-skip-permissions",
        ]
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_weekly_command_with_mention_users(self, mock_popen):
        # Given: weekly_report 커맨드로 생성된 실행기
        executor = ClaudeCLIExecutor(command="weekly_report")
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: mention_users와 함께 execute를 호출하면
        executor.execute("MAI", "@홍길동 @김철수")

        # Then: mention_users가 포함된 /weekly_report 커맨드가 실행된다
        expected_command = [
            "claude",
            "-p",
            '/weekly_report MAI "@홍길동 @김철수"',
            "--dangerously-skip-permissions",
        ]
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    def test_should_default_to_daily_report_command(self):
        # Given/When: 기본 생성자로 실행기를 생성하면
        executor = ClaudeCLIExecutor()

        # Then: daily_report가 기본 커맨드이다
        assert executor._command == "daily_report"


class TestGeminiCLIExecutorWeeklyCommand:
    """Gemini CLI 실행기 weekly_report 커맨드 테스트"""

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_weekly_command_without_mention_users(self, mock_popen):
        # Given: weekly_report 커맨드로 생성된 실행기
        executor = GeminiCLIExecutor(command="weekly_report")
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        executor.execute("MAI")

        # Then: /weekly_report 커맨드가 실행된다
        expected_command = ["gemini", "-p", "/weekly_report MAI"]
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_weekly_command_with_mention_users(self, mock_popen):
        # Given: weekly_report 커맨드로 생성된 실행기
        executor = GeminiCLIExecutor(command="weekly_report")
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: mention_users와 함께 execute를 호출하면
        executor.execute("MAI", "@홍길동")

        # Then: mention_users가 포함된 /weekly_report 커맨드가 실행된다
        expected_command = ["gemini", "-p", '/weekly_report MAI "@홍길동"']
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    def test_should_default_to_daily_report_command(self):
        # Given/When: 기본 생성자로 실행기를 생성하면
        executor = GeminiCLIExecutor()

        # Then: daily_report가 기본 커맨드이다
        assert executor._command == "daily_report"
