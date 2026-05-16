"""StdoutAdapter 단위 테스트 — plan Task 3.

카테고리: [Happy] / [Boundary] — CLAUDE.md Test Coverage Categories.
[Error] 부재 사유: 외부 의존성·IO 분기 없는 순수 print 어댑터.
"""

from src.infrastructure.adapters.stdout_adapter import StdoutAdapter


class TestStdoutAdapter:
    """NotificationPort 구현체 — stdout 출력으로 Slack 대체."""

    # ---------- [Happy] ----------
    def test_should_print_main_message_to_stdout(self, capsys):
        # Given: adapter
        adapter = StdoutAdapter()
        # When: send만 호출
        adapter.send("Hello world")
        # Then: stdout에 본문이 포함
        captured = capsys.readouterr()
        assert "Hello world" in captured.out

    def test_should_print_thread_message_with_separator_when_provided(self, capsys):
        # Given
        adapter = StdoutAdapter()
        # When: main + thread
        adapter.send("Title", "Body content")
        # Then: 본문 + 구분선(─) + thread_message
        captured = capsys.readouterr()
        assert "Title" in captured.out
        assert "Body content" in captured.out
        assert "─" in captured.out

    def test_should_print_multiline_message_preserving_line_breaks(self, capsys):
        # Given
        adapter = StdoutAdapter()
        multiline = "Line 1\nLine 2\nLine 3"
        # When
        adapter.send(multiline)
        # Then: 모든 라인이 출력
        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        assert "Line 3" in captured.out

    # ---------- [Boundary] ----------
    def test_should_not_print_separator_when_thread_message_none(self, capsys):
        # Given
        adapter = StdoutAdapter()
        # When: thread_message=None (default)
        adapter.send("Only main")
        # Then: 구분선 없음
        captured = capsys.readouterr()
        assert "─" not in captured.out

    def test_should_not_print_separator_when_thread_message_empty_string(self, capsys):
        # Given: thread_message=""
        adapter = StdoutAdapter()
        # When
        adapter.send("Only main", "")
        # Then: 빈 문자열은 None과 동등하게 취급 (구분선 없음)
        captured = capsys.readouterr()
        assert "─" not in captured.out

    def test_should_print_empty_main_message_as_blank_line(self, capsys):
        # Given
        adapter = StdoutAdapter()
        # When: 빈 본문
        adapter.send("")
        # Then: print("") → 한 줄의 빈 출력 (\n 한 개)
        captured = capsys.readouterr()
        assert captured.out == "\n"

    def test_should_handle_unicode_korean_characters(self, capsys):
        # Given: 한글 + 이모지 (실제 daily report 포맷)
        adapter = StdoutAdapter()
        # When
        adapter.send("📊 한글 메시지", "🔄 진행 중 - 홍길동")
        # Then: 유니코드가 안전하게 출력
        captured = capsys.readouterr()
        assert "📊" in captured.out
        assert "한글 메시지" in captured.out
        assert "🔄" in captured.out
        assert "홍길동" in captured.out
