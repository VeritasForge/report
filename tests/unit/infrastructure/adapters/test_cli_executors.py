"""CLI 실행기 테스트 — Claude는 claude-agent-sdk mock, Gemini는 subprocess mock."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
)

from src.infrastructure.adapters.cli_executors import (
    ClaudeCLIExecutor,
    GeminiCLIExecutor,
)


# ----------------------------- 헬퍼 -----------------------------

def _assistant(*texts: str) -> AssistantMessage:
    """주어진 text들을 TextBlock 리스트로 갖는 AssistantMessage 생성."""
    return AssistantMessage(
        content=[TextBlock(text=t) for t in texts],
        model="claude-sonnet-4-6",
    )


def _make_fake_query(messages, captured: dict | None = None):
    """SDK query를 흉내내는 async generator factory.

    captured dict가 주어지면 호출 시 kwargs를 기록.
    """

    async def fake(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        for m in messages:
            yield m

    return fake


def _make_raising_query(exc: BaseException):
    """첫 yield 전에 예외를 raise하는 async generator factory."""

    async def fake(**kwargs):
        raise exc
        yield  # pragma: no cover (unreachable but makes this an async generator)

    return fake


# ----------------------------- Claude SDK 테스트 (Task 6) -----------------------------

class TestClaudeCLIExecutor:
    """ClaudeCLIExecutor (claude-agent-sdk 기반).

    카테고리: [Happy] / [Boundary] / [Error] — CLAUDE.md Test Coverage Categories.
    """

    # ---------- [Happy] ----------
    def test_should_call_query_with_correct_prompt(self):
        # Given/When: 기본 호출
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI")
        # Then: prompt에 슬래시 커맨드 + space_key
        assert captured["prompt"] == "/daily_report MAI"

    def test_should_pass_model_option_to_sdk_default_sonnet(self):
        # Given: 생성자 model 미지정
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI")
        # Then: options.model == "sonnet"
        assert captured["options"].model == "sonnet"

    def test_should_pass_explicit_model_to_sdk_when_constructor_arg_given(self):
        # Given: 생성자 model="haiku"
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor(model="haiku").execute("MAI")
        # Then
        assert captured["options"].model == "haiku"

    def test_should_pass_permission_mode_acceptEdits(self):
        # Given: Task 0 스파이크 채택값
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI")
        # Then
        assert captured["options"].permission_mode == "acceptEdits"

    def test_should_pass_cwd_path_cwd_to_sdk(self):
        # Given/When
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI")
        # Then: cwd가 현재 작업 디렉토리
        assert captured["options"].cwd == Path.cwd()

    def test_should_concatenate_textblocks_from_assistant_messages(self):
        # Given: 한 메시지에 여러 TextBlock
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("Hello", "World")]),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then: '\n'으로 join
        assert result == "Hello\nWorld"

    def test_should_include_mention_users_in_prompt(self):
        # Given
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI", "@홍길동 @김철수")
        # Then
        assert captured["prompt"] == '/daily_report MAI "@홍길동 @김철수"'

    def test_should_include_report_date_in_prompt_when_provided(self):
        # Given
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI", "@홍길동", report_date=date(2026, 4, 6))
        # Then
        assert captured["prompt"] == '/daily_report MAI "@홍길동" --date 2026-04-06'

    # ---------- [Boundary] ----------
    def test_should_return_empty_string_when_no_textblocks(self):
        # Given: AssistantMessage가 content 비어있음
        empty_msg = AssistantMessage(content=[], model="claude-sonnet-4-6")
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([empty_msg]),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then: 빈 문자열 (strip 후)
        assert result == ""

    def test_should_ignore_tooluse_blocks_in_assistant_message(self):
        # Given: TextBlock + ToolUseBlock 혼재
        msg = AssistantMessage(
            content=[
                TextBlock(text="result"),
                ToolUseBlock(id="t1", name="some_tool", input={"k": "v"}),
            ],
            model="claude-sonnet-4-6",
        )
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([msg]),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then: TextBlock만 누적
        assert result == "result"

    def test_should_ignore_non_assistant_messages(self):
        # Given: SystemMessage, ResultMessage 등 비-AssistantMessage 무시
        # 실제 SDK SystemMessage / ResultMessage 인스턴스화는 어렵기에 MagicMock으로 대체
        non_assistant = MagicMock(spec=SystemMessage)
        assistant = _assistant("real content")
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([non_assistant, assistant]),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then: AssistantMessage만 처리됨
        assert result == "real content"

    def test_should_concatenate_multiple_assistant_messages(self):
        # Given: 여러 turn (멀티 AssistantMessage)
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("turn1"), _assistant("turn2")]),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then: 모두 누적
        assert "turn1" in result
        assert "turn2" in result

    def test_should_strip_leading_and_trailing_whitespace_from_output(self):
        # Given: 텍스트에 앞뒤 공백
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("  hello  \n")]),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then: strip
        assert result == "hello"

    def test_should_omit_report_date_from_prompt_when_none(self):
        # Given
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI", "@홍길동", report_date=None)
        # Then: --date 미포함
        assert "--date" not in captured["prompt"]

    def test_should_omit_mention_users_from_prompt_when_empty_string(self):
        # Given
        captured: dict = {}
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_fake_query([_assistant("ok")], captured=captured),
        ):
            ClaudeCLIExecutor().execute("MAI", "")
        # Then: 따옴표 mention 미포함
        assert captured["prompt"] == "/daily_report MAI"

    def test_should_accept_model_parameter_in_constructor(self):
        # Given/When (Task 5 케이스 유지)
        executor = ClaudeCLIExecutor(model="sonnet")
        # Then
        assert executor._model == "sonnet"

    def test_should_default_model_to_none_when_not_provided(self):
        # Given/When
        executor = ClaudeCLIExecutor()
        # Then
        assert executor._model is None

    # ---------- [Error] ----------
    def test_should_return_none_on_cli_not_found_error(self):
        # Given: SDK가 CLINotFoundError 발생
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_raising_query(CLINotFoundError("claude not found")),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then: None 반환
        assert result is None

    def test_should_return_none_on_process_error(self):
        # Given: SDK가 ProcessError 발생
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_raising_query(ProcessError("subprocess died")),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then
        assert result is None

    def test_should_return_none_on_cli_json_decode_error(self):
        # Given: SDK 출력 파싱 실패
        # CLIJSONDecodeError 시그니처에 따라 인스턴스화 — 안전하게 args만 전달
        try:
            err = CLIJSONDecodeError("bad json", ValueError("parse failed"))
        except TypeError:
            err = CLIJSONDecodeError("bad json")  # fallback for different sig
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_raising_query(err),
        ):
            result = ClaudeCLIExecutor().execute("MAI")
        # Then
        assert result is None

    def test_should_propagate_unexpected_exception(self):
        # Given: SDK가 잡지 않는 예외(예: RuntimeError) → 호출자에게 노출
        with patch(
            "src.infrastructure.adapters.cli_executors.query",
            new=_make_raising_query(RuntimeError("boom")),
        ):
            # Then: RuntimeError 전파
            with pytest.raises(RuntimeError, match="boom"):
                ClaudeCLIExecutor().execute("MAI")


# ----------------------------- Gemini subprocess 테스트 (변경 없음) -----------------------------

class TestGeminiCLIExecutor:
    """Gemini CLI 실행기 테스트 (subprocess 유지)."""

    @pytest.fixture
    def executor(self):
        return GeminiCLIExecutor()

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_execute_command_successfully(self, mock_popen, executor):
        # Given
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Report content", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        # When
        result = executor.execute("MAI")
        # Then
        assert result == "Report content"

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_correct_command_without_mention_users(self, mock_popen, executor):
        # Given
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        # When
        executor.execute("MAI")
        # Then
        expected_command = ["gemini", "-p", "/daily_report MAI"]
        mock_popen.assert_called_once()
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_correct_command_with_mention_users(self, mock_popen, executor):
        # Given
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        # When
        executor.execute("MAI", "@홍길동")
        # Then
        expected_command = ["gemini", "-p", '/daily_report MAI "@홍길동"']
        mock_popen.assert_called_once()
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_command_fails(self, mock_popen, executor):
        # Given
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        # When
        result = executor.execute("MAI")
        # Then
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_cli_not_found(self, mock_popen, executor):
        # Given
        mock_popen.side_effect = FileNotFoundError()
        # When
        result = executor.execute("MAI")
        # Then
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_return_none_when_unexpected_error_occurs(self, mock_popen, executor):
        # Given
        mock_popen.side_effect = Exception("Unexpected error")
        # When
        result = executor.execute("MAI")
        # Then
        assert result is None

    @patch("src.infrastructure.adapters.cli_executors.subprocess.Popen")
    def test_should_build_command_with_report_date(self, mock_popen, executor):
        # Given
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        # When
        executor.execute("MAI", "@홍길동", report_date=date(2026, 4, 6))
        # Then
        expected_command = ["gemini", "-p", '/daily_report MAI "@홍길동" --date 2026-04-06']
        actual_command = mock_popen.call_args[0][0]
        assert actual_command == expected_command
