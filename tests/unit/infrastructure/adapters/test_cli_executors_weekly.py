"""CLI 실행기 weekly_report 커맨드 테스트 — Claude는 SDK mock."""

from unittest.mock import patch

from claude_agent_sdk import AssistantMessage, TextBlock

from src.infrastructure.adapters.cli_executors import ClaudeCLIExecutor


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
