"""CLI 실행기 테스트"""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.adapters.cli_executors import (
    ClaudeCLIExecutor,
    GeminiCLIExecutor,
)


class TestClaudeCLIExecutor:
    """Claude CLI 실행기 테스트"""

    @pytest.fixture
    def executor(self):
        """테스트용 실행기 인스턴스"""
        return ClaudeCLIExecutor()

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_execute_command_successfully(self, mock_popen, executor):
        # Given: CLI가 성공적으로 실행되는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Report content", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: 출력을 반환한다
        assert result == "Report content"

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_correct_command_without_mention_users(
        self, mock_popen, executor
    ):
        # Given: mention_users가 없는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        executor.execute("MAI")

        # Then: 올바른 커맨드가 실행된다
        expected_command = [
            "claude",
            "-p",
            "/daily_report MAI",
            "--dangerously-skip-permissions",
        ]
        mock_popen.assert_called_once()
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_correct_command_with_mention_users(
        self, mock_popen, executor
    ):
        # Given: mention_users가 있는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        executor.execute("MAI", "@홍길동 @김철수")

        # Then: mention_users가 포함된 커맨드가 실행된다
        expected_command = [
            "claude",
            "-p",
            '/daily_report MAI "@홍길동 @김철수"',
            "--dangerously-skip-permissions",
        ]
        mock_popen.assert_called_once()
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_command_fails(self, mock_popen, executor):
        # Given: CLI가 에러를 반환하는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: None을 반환한다
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_cli_not_found(self, mock_popen, executor):
        # Given: CLI가 설치되지 않은 상황
        mock_popen.side_effect = FileNotFoundError()

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: None을 반환한다
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_unexpected_error_occurs(
        self, mock_popen, executor
    ):
        # Given: 예상치 못한 에러가 발생하는 상황
        mock_popen.side_effect = Exception("Unexpected error")

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: None을 반환한다
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_strip_output(self, mock_popen, executor):
        # Given: 출력에 공백이 포함된 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("  Report content  \n", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: 공백이 제거된 출력을 반환한다
        assert result == "Report content"


class TestGeminiCLIExecutor:
    """Gemini CLI 실행기 테스트"""

    @pytest.fixture
    def executor(self):
        """테스트용 실행기 인스턴스"""
        return GeminiCLIExecutor()

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_execute_command_successfully(self, mock_popen, executor):
        # Given: CLI가 성공적으로 실행되는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Report content", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: 출력을 반환한다
        assert result == "Report content"

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_correct_command_without_mention_users(
        self, mock_popen, executor
    ):
        # Given: mention_users가 없는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        executor.execute("MAI")

        # Then: gemini 커맨드가 실행된다
        expected_command = ["gemini", "-p", "/daily_report MAI"]
        mock_popen.assert_called_once()
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_correct_command_with_mention_users(
        self, mock_popen, executor
    ):
        # Given: mention_users가 있는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        executor.execute("MAI", "@홍길동")

        # Then: mention_users가 포함된 커맨드가 실행된다
        expected_command = ["gemini", "-p", '/daily_report MAI "@홍길동"']
        mock_popen.assert_called_once()
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_command_fails(self, mock_popen, executor):
        # Given: CLI가 에러를 반환하는 상황
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: None을 반환한다
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_cli_not_found(self, mock_popen, executor):
        # Given: CLI가 설치되지 않은 상황
        mock_popen.side_effect = FileNotFoundError()

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: None을 반환한다
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_unexpected_error_occurs(
        self, mock_popen, executor
    ):
        # Given: 예상치 못한 에러가 발생하는 상황
        mock_popen.side_effect = Exception("Unexpected error")

        # When: execute를 호출하면
        result = executor.execute("MAI")

        # Then: None을 반환한다
        assert result is None
